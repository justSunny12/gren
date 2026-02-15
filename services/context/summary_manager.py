# services/context/summary_manager.py
"""
Менеджер для координации фоновых суммаризаций.
"""
import time
from typing import Dict, Any, Optional, Callable, List

from models.summary_task import SummaryTask
from services.context.scheduler import TaskScheduler
from services.context.worker import SummaryWorker


class SummaryManager:
    """Высокоуровневый менеджер фоновых суммаризаций."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        perf_config = config.get("performance", {})
        self.delay_ms = perf_config.get("summary_delay_ms", 1000)
        self.max_workers = perf_config.get("max_background_tasks", 1)

        self.scheduler = TaskScheduler()
        self.worker = SummaryWorker(config, self.scheduler, self.delay_ms)

        self._total_tasks = 0
        self._successful_tasks = 0
        self._failed_tasks = 0

    def start(self):
        """Запускает воркер."""
        self.worker.start()
        # print("🚀 Менеджер суммаризаций запущен")

    def stop(self):
        """Останавливает воркер."""
        self.worker.stop()
        # print("🛑 Менеджер суммаризаций остановлен")

    def schedule_l1_summary(self, text: str, callback: Optional[Callable] = None,
                            priority: int = 1, **kwargs) -> str:
        """Планирует L1 суммаризацию."""
        task_id = f"l1_{int(time.time()*1000)}_{hash(text) % 10000:04d}"
        task = SummaryTask(
            task_id=task_id,
            task_type="l1",
            data=text,
            priority=priority,
            callback=callback,
            extra_params=kwargs
        )
        self.scheduler.put(task)
        self._total_tasks += 1
        return task_id

    def schedule_l2_summary(self, text: str, original_char_count: int, l1_chunk_ids: List[str],
                            callback: Optional[Callable] = None, priority: int = 5, **kwargs) -> str:
        """Планирует L2 суммаризацию."""
        data = {
            "text": text,
            "original_char_count": original_char_count,
            "l1_chunk_ids": l1_chunk_ids
        }
        task_id = f"l2_{int(time.time()*1000)}_{hash(str(l1_chunk_ids)) % 10000:04d}"
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

    # При необходимости можно добавить методы для получения статистики