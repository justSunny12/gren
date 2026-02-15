# services/context/trigger.py
"""
Стратегия принятия решений о запуске суммаризации.
"""
from typing import Optional


class SummarizationTrigger:
    """Определяет, когда нужно запускать L1 или L2 суммаризацию."""

    def __init__(self, config: dict):
        structure = config.get("structure", {})
        raw_tail_config = structure.get("raw_tail", {})
        thresholds = structure.get("thresholds", {})

        self.raw_tail_char_limit = raw_tail_config.get("char_limit", 2000)
        self.l1_summary_threshold = thresholds.get("l2_trigger_count", 4)

    def should_trigger_l1(self, raw_tail: str) -> bool:
        """Проверяет, нужно ли запустить L1 суммаризацию из-за переполнения."""
        return len(raw_tail) > self.raw_tail_char_limit

    def should_trigger_l2(self, l1_chunks_count: int) -> bool:
        """Проверяет, нужно ли запустить L2 суммаризацию."""
        return l1_chunks_count >= self.l1_summary_threshold