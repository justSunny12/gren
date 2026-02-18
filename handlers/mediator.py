# handlers/mediator.py
from typing import Dict, Callable, Any
import json
from container import container

class UIMediator:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._setup_default_handlers()
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    def _setup_default_handlers(self):
        from .commands import CommandHandler
        from .chat_operations import ChatOperationsHandler
        from .chat_list import ChatListHandler
        from .message_handler import MessageHandler
        from .initialization import InitializationHandler
        self._command_handler = CommandHandler()
        self._chat_ops_handler = ChatOperationsHandler()
        self._chat_list_handler = ChatListHandler()
        self._init_handler = InitializationHandler()
        self._message_handler = MessageHandler()
        self.register("get_chat_list_data", self._chat_list_handler.get_chat_list_data)
        self.register("handle_chat_selection", self._handle_chat_selection)
        self.register("create_chat", self._chat_ops_handler.create_chat_with_js_handler)
        self.register("send_message_stream", self._message_handler.send_message_stream_handler)
        self.register("init_app", self._init_handler.init_app_handler)
        self.register("stop_generation", self._message_handler.stop_active_generation)
        self.register("get_current_settings", self._get_current_settings_handler)

    def register(self, event_type: str, handler: Callable):
        self._handlers[event_type] = handler

    def dispatch(self, event_type: str, *args, **kwargs) -> Any:
        if event_type not in self._handlers:
            self.logger.error("Обработчик не найден для события: %s", event_type)
            raise ValueError(f"Обработчик не найден для события: {event_type}")
        try:
            return self._handlers[event_type](*args, **kwargs)
        except Exception as e:
            self.logger.exception("Ошибка при выполнении события %s: %s", event_type, e)
            raise

    def _handle_chat_selection(self, chat_id: str):
        if not chat_id:
            return [], "", self._chat_list_handler.get_chat_list_data()
        if chat_id.startswith('delete:'):
            return self._command_handler.handle_chat_deletion(chat_id)
        elif chat_id.startswith('rename:'):
            return self._command_handler.handle_chat_rename(chat_id)
        elif chat_id.startswith('pin:') or chat_id.startswith('unpin:'):
            return self._command_handler.handle_chat_pinning(chat_id)
        elif chat_id.startswith('thinking:'):
            history, new_id, chat_list_data = self._command_handler.handle_thinking_toggle(chat_id)
            if history is None:
                current_dialog = self._command_handler.dialog_service.get_current_dialog()
                history = current_dialog.to_ui_format() if current_dialog else []
                new_id = current_dialog.id if current_dialog else ""
            return history, new_id, chat_list_data
        elif chat_id.startswith('settings:apply:'):
            return self._command_handler.handle_settings_apply(chat_id)
        else:
            return self._chat_ops_handler.handle_chat_switch(chat_id)

    def _get_current_settings_handler(self):
        from container import container
        from services.user_config_service import user_config_service

        config_service = container.get("config_service")
        
        default_config = config_service.get_default_config()
        gen_defaults = default_config.get("generation", {})

        user_config = user_config_service.get_user_config(force_reload=True)

        current_max_tokens = user_config.generation.max_tokens
        if current_max_tokens is None:
            current_max_tokens = gen_defaults.get("default_max_tokens", 2048)

        current_temperature = user_config.generation.temperature
        if current_temperature is None:
            current_temperature = gen_defaults.get("default_temperature", 0.7)

        data = {
            "current_max_tokens": current_max_tokens,
            "current_temperature": current_temperature,
            "default_max_tokens": gen_defaults.get("default_max_tokens", 2048),
            "default_temperature": gen_defaults.get("default_temperature", 0.7),
            "min_max_tokens": gen_defaults.get("min_max_tokens", 64),
            "max_max_tokens": gen_defaults.get("max_max_tokens", 4096),
            "step_max_tokens": 64,
            "min_temperature": gen_defaults.get("min_temperature", 0.1),
            "max_temperature": gen_defaults.get("max_temperature", 1.5),
            "step_temperature": 0.05
        }
        return json.dumps(data, ensure_ascii=False)

    def get_chat_list_data(self, scroll_target: str = 'none'):
        return self.dispatch("get_chat_list_data", scroll_target)

    def handle_chat_selection(self, chat_id: str):
        return self.dispatch("handle_chat_selection", chat_id)

    def create_chat_with_js_handler(self):
        return self.dispatch("create_chat")

    async def send_message_stream_handler(self, prompt, chat_id, max_tokens, temperature, search_enabled=False):
        async for result in self.dispatch("send_message_stream", prompt, chat_id, max_tokens, temperature, search_enabled):
            yield result

    def init_app_handler(self):
        return self.dispatch("init_app")

    def stop_active_generation(self):
        return self.dispatch("stop_generation")

    def get_current_settings(self):
        return self.dispatch("get_current_settings")

ui_handlers = UIMediator()