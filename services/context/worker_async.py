# services/context/worker_async.py
import asyncio
import threading
from typing import Dict, Any, Optional, Callable

from services.context.summarizer_factory import SummarizerFactory
from container import container


class AsyncSummaryWorker:
    """
    Асинхронный воркер, работающий в отдельном потоке с собственным event loop.
    Управляет очередью задач и выполняет их конкурентно.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._async_stop = asyncio.Event()  # асинхронный сигнал остановки
        self._task_queue: Optional[asyncio.Queue] = None
        self._logger = container.get_logger()
        self._queue_ready = threading.Event()

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._async_stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._queue_ready.wait(timeout=5)

    def stop(self):
        """Инициирует мягкое завершение работы воркера."""
        self._stop_event.set()
        # Устанавливаем асинхронный сигнал остановки
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._async_stop.set)
        if self._thread:
            self._thread.join(timeout=10)

    def _run_loop(self):
        """Запускает asyncio event loop в текущем потоке."""
        asyncio.run(self._async_main())

    async def _async_main(self):
        """Главная корутина, управляющая жизненным циклом воркера."""
        self._loop = asyncio.get_running_loop()
        self._task_queue = asyncio.Queue()
        self._queue_ready.set()

        summarizers = SummarizerFactory.get_all_summarizers(self.config)

        # Создаём задачу для обработки очереди
        processor_task = asyncio.create_task(self._process_tasks(summarizers))
        # Создаём задачу для ожидания сигнала остановки
        stop_task = asyncio.create_task(self._async_stop.wait())

        # Ждём либо завершения обработчика (маловероятно), либо сигнала остановки
        done, pending = await asyncio.wait(
            [processor_task, stop_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Если остановка – отменяем обработчик
        if stop_task in done:
            processor_task.cancel()
            try:
                await processor_task
            except asyncio.CancelledError:
                pass

        # Если обработчик завершился сам (например, из-за ошибки) – просто выходим

        # Дожидаемся завершения всех задач в очереди
        if not self._task_queue.empty():
            self._logger.debug("⏳ [AsyncWorker] Ожидание завершения оставшихся задач...")
            await self._task_queue.join()

        self._logger.debug("✅ [AsyncWorker] Завершение работы")

    async def _process_tasks(self, summarizers):
        """Обрабатывает задачи из очереди, пока не будет сигнала остановки."""
        while not self._async_stop.is_set():
            # Ждём задачу из очереди (блокируется до появления задачи)
            task = await self._task_queue.get()

            self._logger.debug(f"📥 [AsyncWorker] Получена задача {task['task_id']} типа {task['task_type']}")

            # Задержка перед выполнением (если задана)
            delay = self.config.get("performance", {}).get("summary_delay_ms", 1000) / 1000.0
            if delay > 0:
                await asyncio.sleep(delay)

            try:
                if task["task_type"] == "l1":
                    summarizer = summarizers["l1"]
                    result = await summarizer.summarize(
                        task["text"],
                        **task.get("params", {})
                    )
                    if result.success and task.get("callback"):
                        task["callback"](result.summary, task["data"])
                elif task["task_type"] == "l2":
                    summarizer = summarizers["l2"]
                    result = await summarizer.summarize(
                        task["text"],
                        **task.get("params", {})
                    )
                    if result.success and task.get("callback"):
                        task["callback"](
                            result.summary,
                            task["data"]["text"],
                            task["data"]["l1_chunk_ids"],
                            task["data"]["original_char_count"]
                        )
                else:
                    self._logger.error(f"❌ [AsyncWorker] Неизвестный тип задачи: {task['task_type']}")
            except Exception as e:
                self._logger.error(f"❌ [AsyncWorker] Ошибка при обработке задачи: {e}", exc_info=True)
            finally:
                self._task_queue.task_done()

    def submit_task(self, task_type: str, text: str, callback: Optional[Callable] = None,
                    data: Optional[Dict] = None, params: Optional[Dict] = None) -> str:
        """Добавляет задачу в очередь (вызывается из любого потока)."""
        if self._task_queue is None:
            raise RuntimeError("Воркер ещё не запущен или очередь не создана")

        task_id = f"{task_type}_{id(text)}_{threading.get_ident()}"
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "text": text,
            "callback": callback,
            "data": data or {},
            "params": params or {}
        }
        self._loop.call_soon_threadsafe(self._task_queue.put_nowait, task)
        self._logger.debug(f"📤 [AsyncWorker] Задача {task_id} добавлена в очередь")
        return task_id