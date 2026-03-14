# services/context/worker.py
"""
Воркер, выполняющий задачи суммаризации в фоновом потоке с переиспользованием event loop.
"""
import time
import asyncio
import threading
from typing import Dict, Any

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

    def stop(self):
        self.stop_event.set()
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self.thread:
            self.thread.join(timeout=5.0)

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            while not self.stop_event.is_set():
                task = self.scheduler.get(timeout=0.5)
                if task is None:
                    continue

                if time.time() - task.created_at < self.delay:
                    time.sleep(self.delay)

                try:
                    summarizers = self._get_summarizers()
                    if task.task_type == "l1":
                        summarizer = summarizers["l1"]
                        result = self._loop.run_until_complete(
                            summarizer.summarize(task.data["text"], **task.extra_params)
                        )
                        if task.callback and result.success:
                            task.callback(result.summary, task.data)  # data содержит dialog_id
                    elif task.task_type == "l2":
                        summarizer = summarizers["l2"]
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
                    else:
                        raise ValueError(f"Unknown task type: {task.task_type}")

                    self.scheduler.task_done()
                except Exception as e:
                    self.logger.error("Ошибка в воркере: %s", e)
                    self.scheduler.task_done()
        finally:
            if self._loop is not None:
                self._loop.close()
                self._loop = None