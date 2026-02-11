# services/context/factory.py (исправленная версия)
"""
Фабрика для создания менеджеров контекста
"""
import threading
from typing import Dict, Optional, Any
from container import container

from services.context.manager import ContextManager
from models.dialog import Dialog


class ContextManagerFactory:
    """Фабрика для создания и управления менеджерами контекста"""
    
    _instances: Dict[str, ContextManager] = {}
    _lock = threading.RLock()
    
    @classmethod
    def get_for_dialog(cls, dialog: Dialog) -> ContextManager:
        """Получает или создает менеджер контекста для диалога"""
        with cls._lock:
            if dialog.id in cls._instances:
                return cls._instances[dialog.id]
            
            # Создаем новый менеджер
            config_service = container.get("config_service")
            config = config_service.get_config().get("context", {})
            
            if not config.get("enabled", True):
                # Если контекст отключен, возвращаем заглушку
                from services.context.dummy_manager import DummyContextManager
                manager = DummyContextManager(dialog, config)
            else:
                manager = ContextManager(dialog, config)
            
            cls._instances[dialog.id] = manager
            return manager
    
    @classmethod
    def remove_for_dialog(cls, dialog_id: str):
        """Удаляет менеджер контекста для диалога"""
        with cls._lock:
            if dialog_id in cls._instances:
                manager = cls._instances.pop(dialog_id)
                try:
                    manager.cleanup()
                except:
                    pass