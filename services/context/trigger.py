# services/context/trigger.py
"""
Стратегия принятия решений о запуске суммаризации.
"""
from typing import Optional
from container import container


class SummarizationTrigger:
    """Определяет, когда нужно запускать L1 или L2 суммаризацию."""

    def __init__(self, config: dict):
        structure = config.get("structure", {})
        raw_tail_config = structure.get("raw_tail", {})
        thresholds = structure.get("thresholds", {})

        self.raw_tail_char_limit = raw_tail_config.get("char_limit", 2000)
        self.l1_summary_threshold = thresholds.get("l2_trigger_count", 4)
        self._logger = container.get_logger()

    def should_trigger_l1(self, raw_tail: str) -> bool:
        """Проверяет, нужно ли запустить L1 суммаризацию из-за переполнения."""
        current_len = len(raw_tail)
        limit = self.raw_tail_char_limit
        triggered = current_len > limit
        if triggered:
            self._logger.debug(f"🚨 [Trigger] L1 триггер: {current_len} > {limit}")
        else:
            self._logger.debug(f"📏 [Trigger] L1 не требуется: {current_len} <= {limit}")
        return triggered

    def should_trigger_l2(self, l1_chunks_count: int) -> bool:
        """Проверяет, нужно ли запустить L2 суммаризацию."""
        triggered = l1_chunks_count >= self.l1_summary_threshold
        if triggered:
            self._logger.debug(f"🚨 [Trigger] L2 триггер: {l1_chunks_count} >= {self.l1_summary_threshold}")
        else:
            self._logger.debug(f"📏 [Trigger] L2 не требуется: {l1_chunks_count} < {self.l1_summary_threshold}")
        return triggered