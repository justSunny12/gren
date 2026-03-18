# services/context/global_manager.py
"""
Глобальный менеджер суммаризации для всех диалогов.
Использует AsyncSummaryWorker для асинхронной обработки.
"""
import threading
import asyncio
from typing import Dict, Any, Optional, Callable, List

from services.context.worker_async import AsyncSummaryWorker
from container import container


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
        self.worker = AsyncSummaryWorker(self.config)
        self._logger = container.get_logger()

    def start(self):
        """Запускает асинхронный воркер."""
        self.worker.start()
        self._logger.info("   ✅ Глобальный менеджер суммаризаций запущен")

    def stop(self):
        """Останавливает воркер."""
        self.worker.stop()
        self._logger.info("🛑 Глобальный менеджер суммаризаций остановлен")

    def schedule_l1_summary(
        self,
        dialog_id: str,
        text: str,
        callback: Optional[Callable] = None,
        **kwargs
    ) -> str:
        """Планирует L1 суммаризацию для конкретного диалога."""
        data = {"dialog_id": dialog_id, "text": text}
        return self.worker.submit_task(
            task_type="l1",
            text=text,
            callback=callback,
            data=data,
            params=kwargs
        )

    def schedule_l2_summary(
        self,
        dialog_id: str,
        text: str,
        original_char_count: int,
        l1_chunk_ids: List[str],
        callback: Optional[Callable] = None,
        **kwargs
    ) -> str:
        """Планирует L2 суммаризацию для конкретного диалога."""
        data = {
            "dialog_id": dialog_id,
            "text": text,
            "original_char_count": original_char_count,
            "l1_chunk_ids": l1_chunk_ids
        }
        return self.worker.submit_task(
            task_type="l2",
            text=text,
            callback=callback,
            data=data,
            params=kwargs
        )

    def run_coro(self, coro):
        """
        Запускает корутину в event loop воркера.
        Возвращает concurrent.futures.Future.
        """
        if self.worker._loop is None:
            raise RuntimeError("Воркер не запущен")
        return asyncio.run_coroutine_threadsafe(coro, self.worker._loop)

    def get_stats(self) -> Dict[str, Any]:
        return {
            'worker_alive': self.worker._thread is not None and self.worker._thread.is_alive()
        }


# Глобальный экземпляр
global_summary_manager = GlobalSummaryManager()