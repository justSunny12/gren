# services/context/worker.py
"""
Воркер, выполняющий задачи суммаризации в фоновом потоке с постоянным event loop.
"""
import time
import asyncio
import threading
from typing import Dict, Any, Coroutine

from models.summary_task import SummaryTask
from services.context.summarizers import SummaryResult
from services.context.summarizer_factory import SummarizerFactory
from container import container


class SummaryWorker:
    """Выполняет задачи суммаризации в отдельном потоке с постоянным event loop."""

    def __init__(self, config: Dict[str, Any], scheduler, delay_ms: int = 1000):
        self.config = config
        self.scheduler = scheduler
        self.delay = delay_ms / 1000.0
        self.stop_event = threading.Event()
        self.thread = None
        self._summarizers = None
        self._logger = None
        self._loop = None  # Будет создан в потоке

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    def _get_summarizers(self):
        if self._summarizers is None:
            self._summarizers = SummarizerFactory.get_all_summarizers(self.config)
        return self._summarizers

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.logger.debug("🧵 [Worker] Поток воркера запущен")

    def stop(self):
        self.stop_event.set()
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self.thread:
            self.thread.join(timeout=5.0)
        self.logger.debug("🛑 [Worker] Поток воркера остановлен")

    def submit(self, coro: Coroutine):
        """
        Запускает корутину в event loop воркера.
        Возвращает concurrent.futures.Future.
        """
        if self._loop is None:
            raise RuntimeError("Worker event loop not running")
        self.logger.debug("📨 [Worker] Получена корутина для выполнения в фоновом event loop")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self.logger.debug("🧵 [Worker] Event loop создан и запущен")

        try:
            while not self.stop_event.is_set():
                task = self.scheduler.get(timeout=0.5)
                if task is None:
                    continue

                self.logger.debug(f"📥 [Worker] Получена задача {task.task_id} типа {task.task_type}")

                if time.time() - task.created_at < self.delay:
                    wait = self.delay - (time.time() - task.created_at)
                    self.logger.debug(f"⏳ [Worker] Задача {task.task_id} ожидает {wait:.3f} сек (задержка {self.delay} сек)")
                    time.sleep(self.delay)

                try:
                    summarizers = self._get_summarizers()
                    if task.task_type == "l1":
                        summarizer = summarizers["l1"]
                        self.logger.debug(f"▶️ [Worker] Запуск L1 суммаризации для задачи {task.task_id}")
                        result = self._loop.run_until_complete(
                            summarizer.summarize(task.data["text"], **task.extra_params)
                        )
                        if task.callback and result.success:
                            task.callback(result.summary, task.data)
                        self.logger.debug(f"✅ [Worker] Задача {task.task_id} выполнена успешно, время обработки {result.processing_time:.3f} сек")
                    elif task.task_type == "l2":
                        summarizer = summarizers["l2"]
                        self.logger.debug(f"▶️ [Worker] Запуск L2 суммаризации для задачи {task.task_id}")
                        result = self._loop.run_until_complete(
                            summarizer.summarize(task.data["text"], **task.extra_params)
                        )
                        if task.callback and result.success:
                            task.callback(
                                result.summary,
                                task.data["text"],
                                task.data["l1_chunk_ids"],
                                task.data["original_char_count"]
                            )
                        self.logger.debug(f"✅ [Worker] Задача {task.task_id} выполнена успешно, время обработки {result.processing_time:.3f} сек")
                    else:
                        raise ValueError(f"Unknown task type: {task.task_type}")

                    self.scheduler.task_done()
                except Exception as e:
                    self.logger.error(f"❌ [Worker] Ошибка при выполнении задачи {task.task_id}: {e}")
                    self.scheduler.task_done()
        finally:
            if self._loop is not None:
                self._loop.close()
                self._loop = None
            self.logger.debug("🧵 [Worker] Event loop закрыт")