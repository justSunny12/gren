# services/context/global_manager.py
"""
Глобальный менеджер суммаризации для всех диалогов.
"""
import threading
from typing import Dict, Any, Optional, Callable, List

from models.summary_task import SummaryTask
from services.context.scheduler import TaskScheduler
from services.context.worker import SummaryWorker
from container import container
from time import time

class GlobalSummaryManager:
    """Единый менеджер суммаризации для всех диалогов."""

    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        self.config = container.get_config().get("context", {})
        perf_config = self.config.get("performance", {})
        self.delay_ms = perf_config.get("summary_delay_ms", 1000)
        self.max_workers = perf_config.get("max_background_tasks", 1)

        self.scheduler = TaskScheduler()
        self.worker = SummaryWorker(self.config, self.scheduler, self.delay_ms)

        self._total_tasks = 0
        self._successful_tasks = 0
        self._failed_tasks = 0
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    def start(self):
        """Запускает глобальный воркер."""
        self.worker.start()
        self.logger.info("🚀 Глобальный менеджер суммаризаций запущен")

    def stop(self):
        """Останавливает глобальный воркер."""
        self.worker.stop()
        self.logger.info("🛑 Глобальный менеджер суммаризаций остановлен")

    def schedule_l1_summary(
        self,
        dialog_id: str,
        text: str,
        callback: Optional[Callable] = None,
        priority: int = 1,
        **kwargs
    ) -> str:
        """Планирует L1 суммаризацию для конкретного диалога."""
        task_id = f"l1_{dialog_id}_{int(time.time()*1000)}_{hash(text) % 10000:04d}"
        task = SummaryTask(
            task_id=task_id,
            task_type="l1",
            data={"dialog_id": dialog_id, "text": text},
            priority=priority,
            callback=callback,
            extra_params=kwargs
        )
        self.scheduler.put(task)
        self._total_tasks += 1
        return task_id

    def schedule_l2_summary(
        self,
        dialog_id: str,
        text: str,
        original_char_count: int,
        l1_chunk_ids: List[str],
        callback: Optional[Callable] = None,
        priority: int = 5,
        **kwargs
    ) -> str:
        """Планирует L2 суммаризацию для конкретного диалога."""
        data = {
            "dialog_id": dialog_id,
            "text": text,
            "original_char_count": original_char_count,
            "l1_chunk_ids": l1_chunk_ids
        }
        task_id = f"l2_{dialog_id}_{int(time.time()*1000)}_{hash(str(l1_chunk_ids)) % 10000:04d}"
        task = SummaryTask(
            task_id=task_id,
            task_type="l2",
            data=data,
            priority=priority,
            callback=callback,
            extra_params=kwargs
        )
        self.scheduler.put(task)
        self._total_tasks += 1
        return task_id

    def get_stats(self) -> Dict[str, Any]:
        return {
            'total_tasks': self._total_tasks,
            'successful': self._successful_tasks,
            'failed': self._failed_tasks,
            'queue_size': self.scheduler.qsize(),
            'worker_alive': self.worker.thread and self.worker.thread.is_alive()
        }


# Глобальный экземпляр
global_summary_manager = GlobalSummaryManager()