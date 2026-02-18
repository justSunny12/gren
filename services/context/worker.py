# services/context/worker.py
"""
Воркер, выполняющий задачи суммаризации в фоновом потоке.
"""
import time
import asyncio
import threading
from typing import Dict, Any

from models.summary_task import SummaryTask
from services.context.summarizers import SummaryResult
from services.context.summarizer_factory import SummarizerFactory


class SummaryWorker:
    """Выполняет задачи суммаризации в отдельном потоке."""

    def __init__(self, config: Dict[str, Any], scheduler, delay_ms: int = 1000):
        self.config = config
        self.scheduler = scheduler
        self.delay = delay_ms / 1000.0
        self.stop_event = threading.Event()
        self.thread = None
        self._summarizers = None

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
        if self.thread:
            self.thread.join(timeout=5.0)

    def _run(self):
        while not self.stop_event.is_set():
            task = self.scheduler.get(timeout=0.5)
            if task is None:
                continue

            # Задержка для накопления
            if time.time() - task.created_at < self.delay:
                time.sleep(self.delay)

            # Выполнение
            try:
                summarizers = self._get_summarizers()
                if task.task_type == "l1":
                    summarizer = summarizers["l1"]
                    result = asyncio.run(summarizer.summarize(task.data, **task.extra_params))
                elif task.task_type == "l2":
                    summarizer = summarizers["l2"]
                    result = asyncio.run(summarizer.summarize(
                        task.data["text"],
                        **task.extra_params
                    ))
                else:
                    raise ValueError(f"Unknown task type: {task.task_type}")

                if task.callback and result.success:
                    if task.task_type == "l1":
                        task.callback(result.summary, task.data)
                    elif task.task_type == "l2":
                        task.callback(
                            result.summary,
                            task.data["text"],
                            task.data.get("l1_chunk_ids", []),
                            task.data.get("original_char_count", 0)
                        )

                self.scheduler.task_done()
            except Exception as e:
                from container import container
                logger = container.get_logger()
                logger.error("Ошибка в воркере: %s", e)
                self.scheduler.task_done()