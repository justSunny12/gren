# handlers/mediator.py
from typing import Dict, Callable, Any

class UIMediator:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._setup_default_handlers()
    
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
    
    def register(self, event_type: str, handler: Callable):
        self._handlers[event_type] = handler
    
    def dispatch(self, event_type: str, *args, **kwargs) -> Any:
        if event_type not in self._handlers:
            raise ValueError(f"Обработчик не найден для события: {event_type}")
        return self._handlers[event_type](*args, **kwargs)
    
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
        else:
            return self._chat_ops_handler.handle_chat_switch(chat_id)
    
    def get_chat_list_data(self):
        return self.dispatch("get_chat_list_data")
    
    def handle_chat_selection(self, chat_id: str):
        return self.dispatch("handle_chat_selection", chat_id)
    
    def create_chat_with_js_handler(self):
        return self.dispatch("create_chat")
    
    async def send_message_stream_handler(self, prompt, chat_id, max_tokens, temperature):
        async for result in self.dispatch("send_message_stream", prompt, chat_id, max_tokens, temperature):
            yield result
    
    def init_app_handler(self):
        return self.dispatch("init_app")
    
    def stop_active_generation(self):
        return self.dispatch("stop_generation")

ui_handlers = UIMediator()