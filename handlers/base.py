# handlers/base.py
import time
from container import container

class BaseHandler:
    """Базовый класс с общими сервисами и состоянием"""
    
    def __init__(self):
        self._dialog_service = None
        self._config_service = None
        self._last_chat_switch = 0
        self._switch_debounce_ms = 300
    
    @property
    def dialog_service(self):
        """Ленивая загрузка сервиса диалогов"""
        if self._dialog_service is None:
            self._dialog_service = container.get_dialog_service()
        return self._dialog_service
    
    @property
    def config_service(self):
        """Ленивая загрузка сервиса конфигурации"""
        if self._config_service is None:
            self._config_service = container.get("config_service")
        return self._config_service
    
    @property
    def config(self):
        """Быстрый доступ к конфигурации"""
        return self.config_service.get_config()
    
    def check_debounce(self) -> bool:
        """Проверяет, не слишком ли быстро происходит переключение"""
        current_time = time.time() * 1000
        if current_time - self._last_chat_switch < self._switch_debounce_ms:
            return False
        self._last_chat_switch = current_time
        return True

    def get_chat_list_data(self, scroll_target: str = 'none') -> str:
        """Получает данные списка чатов в JSON."""
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data(scroll_target=scroll_target)