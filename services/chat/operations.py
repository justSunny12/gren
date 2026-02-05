# services/chat/operations.py
"""
Операции с состоянием (работа с диалогами, моделью)
"""

from typing import Optional, Dict, Any, List
from container import container


class ChatOperations:
    """Операции с состоянием"""
    
    def __init__(self):
        self._services = {}
    
    def _get_service(self, name):
        """Ленивая загрузка сервиса"""
        if name not in self._services:
            self._services[name] = container.get(name)
        return self._services[name]
    
    @property
    def dialog_service(self):
        return self._get_service("dialog_service")
    
    @property
    def model_service(self):
        return self._get_service("model_service")
    
    @property
    def config_service(self):
        return self._get_service("config_service")
    
    # Диалоги
    def get_dialog(self, dialog_id: str):
        """Получает диалог"""
        return self.dialog_service.get_dialog(dialog_id)
    
    def create_dialog(self, name: Optional[str] = None) -> str:
        """Создает новый диалог"""
        return self.dialog_service.create_dialog(name)
    
    def rename_dialog(self, dialog_id: str, new_name: str) -> bool:
        """Переименовывает диалог"""
        return self.dialog_service.rename_dialog(dialog_id, new_name)
    
    def add_messages(self, dialog_id: str, user_message: str, assistant_message: str) -> bool:
        """Добавляет пару сообщений в диалог"""
        from models.enums import MessageRole
        
        success1 = self.dialog_service.add_message(dialog_id, MessageRole.USER, user_message)
        success2 = self.dialog_service.add_message(dialog_id, MessageRole.ASSISTANT, assistant_message)
        return success1 and success2
    
    # Модель
    def generate_response(self, messages: List[Dict], **params) -> str:
        """Генерирует ответ модели"""
        if not hasattr(self.model_service, 'generate_response'):
            return "Ошибка: сервис модели не поддерживает генерацию"
        
        return self.model_service.generate_response(messages, **params)
    
    # Конфигурация
    def get_config(self) -> Dict[str, Any]:
        """Получает конфигурацию"""
        return self.config_service.get_config()
    
    # Статистика
    def get_model_stats(self) -> Dict[str, Any]:
        """Получает статистику модели"""
        try:
            if hasattr(self.model_service, 'get_stats'):
                stats = self.model_service.get_stats()
                from .formatter import format_model_stats
                return format_model_stats(stats)
        except Exception:
            pass
        return {"status": "Статистика недоступна"}
    
    def get_chat_list_data(self):
        """Получает данные списка чатов"""
        from handlers import ui_handlers
        return ui_handlers.get_chat_list_data()