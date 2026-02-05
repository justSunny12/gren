# handlers/base.py
import time
from container import container

class BaseHandler:
    """Базовый класс с общими сервисами и состоянием"""
    
    def __init__(self):
        self._chat_service = None
        self._dialog_service = None
        self._config_service = None
        self._last_chat_switch = 0
        self._switch_debounce_ms = 300
    
    @property
    def chat_service(self):
        """Ленивая загрузка сервиса чата"""
        if self._chat_service is None:
            self._chat_service = container.get_chat_service()
        return self._chat_service
    
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