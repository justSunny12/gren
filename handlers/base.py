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
        self._logger = None
        self._chat_list_handler = None
        self._ui_mediator = None   # <-- добавлено

    @property
    def ui_mediator(self):
        """Ленивая загрузка UIMediator"""
        if self._ui_mediator is None:
            self._ui_mediator = container.get("ui_mediator")
        return self._ui_mediator

    @property
    def dialog_service(self):
        if self._dialog_service is None:
            self._dialog_service = container.get_dialog_service()
        return self._dialog_service

    @property
    def config_service(self):
        if self._config_service is None:
            self._config_service = container.get("config_service")
        return self._config_service

    @property
    def config(self):
        return self.config_service.get_config()

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    def check_debounce(self) -> bool:
        current_time = time.time() * 1000
        if current_time - self._last_chat_switch < self._switch_debounce_ms:
            return False
        self._last_chat_switch = current_time
        return True

    def get_chat_list_data(self, scroll_target: str = 'none') -> str:
        if self._chat_list_handler is None:
            from .chat_list import ChatListHandler
            self._chat_list_handler = ChatListHandler()
        return self._chat_list_handler.get_chat_list_data(scroll_target=scroll_target)