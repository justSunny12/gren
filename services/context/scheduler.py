# services/context/scheduler.py
"""
Планировщик задач суммаризации с приоритетной очередью.
"""
import queue
import threading
from typing import Optional

from models.summary_task import SummaryTask


class TaskScheduler:
    """Управляет очередью задач с приоритетами."""

    def __init__(self):
        self._queue = queue.PriorityQueue()
        self._task_counter = 0
        self._counter_lock = threading.Lock()

    def put(self, task: SummaryTask):
        """Добавляет задачу в очередь."""
        with self._counter_lock:
            task.sequence_number = self._task_counter
            self._task_counter += 1
        self._queue.put((-task.priority, task))  # отрицательный приоритет для heapq

    def get(self, timeout: Optional[float] = None):
        """Извлекает задачу из очереди (блокирующий вызов)."""
        try:
            priority, task = self._queue.get(timeout=timeout)
            return task
        except queue.Empty:
            return None

    def task_done(self):
        """Сигнализирует о завершении задачи."""
        self._queue.task_done()

    def qsize(self) -> int:
        return self._queue.qsize()