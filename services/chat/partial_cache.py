# services/chat/partial_cache.py
"""
Кэш для частичных обновлений истории во время стриминга.
"""
from typing import List, Dict


class PartialUpdateCache:
    """Временное хранение промежуточных версий истории диалога."""

    def __init__(self):
        self._cache = {}

    def get(self, cache_key: str, base_history: List[Dict]) -> List[Dict]:
        """Возвращает закэшированную историю или создаёт копию базовой."""
        if cache_key not in self._cache:
            self._cache[cache_key] = list(base_history)
        return list(self._cache[cache_key])

    def clear(self, cache_key: str):
        """Инвалидирует запись по ключу."""
        if cache_key in self._cache:
            del self._cache[cache_key]