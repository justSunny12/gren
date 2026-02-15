# models/summary_task.py
"""
Модель задачи суммаризации для очереди.
"""
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
import time


@dataclass
class SummaryTask:
    """Задача суммаризации (сравнимая для PriorityQueue)."""
    task_id: str
    task_type: str  # "l1" или "l2"
    data: Any
    priority: int = 1
    created_at: float = field(default_factory=time.time)
    sequence_number: int = 0
    callback: Optional[Callable] = None
    extra_params: dict = field(default_factory=dict)

    def __lt__(self, other):
        if not isinstance(other, SummaryTask):
            return NotImplemented
        if self.priority != other.priority:
            return self.priority > other.priority  # выше приоритет = меньше для heapq
        return self.sequence_number < other.sequence_number

    def __eq__(self, other):
        if not isinstance(other, SummaryTask):
            return NotImplemented
        return (self.task_id == other.task_id and
                self.priority == other.priority and
                self.sequence_number == other.sequence_number)