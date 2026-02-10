# services/context/background_tasks.py
"""
Управление фоновыми задачами суммаризации
"""
import asyncio
import threading
from typing import Dict, Set
from datetime import datetime

class BackgroundTaskManager:
    """Менеджер фоновых задач суммаризации"""
    
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = threading.RLock()
    
    def schedule_summarization(self, task_id: str, coro):
        """Планирует задачу суммаризации"""
        with self._lock:
            if task_id in self._tasks:
                return False
            
            task = asyncio.create_task(coro)
            self._tasks[task_id] = task
            
            # Добавляем callback для удаления задачи при завершении
            task.add_done_callback(lambda t: self._remove_task(task_id))
            
            return True
    
    def _remove_task(self, task_id: str):
        """Удаляет задачу из списка"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
    
    def cancel_task(self, task_id: str):
        """Отменяет задачу"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].cancel()
                del self._tasks[task_id]
    
    def get_active_tasks(self) -> Set[str]:
        """Возвращает ID активных задач"""
        with self._lock:
            return set(self._tasks.keys())
    
    def stop_all(self):
        """Останавливает все задачи"""
        with self._lock:
            for task_id, task in list(self._tasks.items()):
                task.cancel()
            self._tasks.clear()

# Глобальный экземпляр
background_task_manager = BackgroundTaskManager()