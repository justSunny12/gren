# handlers/mediator.py
from typing import Dict, Callable, Any, Optional

class UIMediator:
    """Медиатор для управления обработчиками UI событий"""
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Регистрация обработчиков по умолчанию"""
        # Импорты внутри методов для избежания циклических зависимостей
        from .commands import CommandHandler
        from .chat_operations import ChatOperationsHandler
        from .chat_list import ChatListHandler
        from .message_handler import MessageHandler
        from .initialization import InitializationHandler
        
        # Создаем экземпляры обработчиков
        self._command_handler = CommandHandler()
        self._chat_ops_handler = ChatOperationsHandler()
        self._chat_list_handler = ChatListHandler()
        self._init_handler = InitializationHandler()
        self._message_handler = MessageHandler()
        
        # Регистрируем методы
        self.register("get_chat_list_data", self._chat_list_handler.get_chat_list_data)
        self.register("handle_chat_selection", self._handle_chat_selection)
        self.register("create_chat", self._chat_ops_handler.create_chat_with_js_handler)
        self.register("send_message_stream", self._message_handler.send_message_stream_handler)
        self.register("init_app", self._init_handler.init_app_handler)
        self.register("stop_generation", self._message_handler.stop_active_generation)
    
    def register(self, event_type: str, handler: Callable):
        """Регистрация обработчика события"""
        self._handlers[event_type] = handler
    
    def dispatch(self, event_type: str, *args, **kwargs) -> Any:
        """Выполнение обработчика события"""
        if event_type not in self._handlers:
            raise ValueError(f"Обработчик не найден для события: {event_type}")
        return self._handlers[event_type](*args, **kwargs)
    
    def _handle_chat_selection(self, chat_id: str):
        """Внутренний обработчик выбора чата с командной логикой"""
        if not chat_id:
            return [], "", self._chat_list_handler.get_chat_list_data()
        
        if chat_id.startswith('delete:'):
            return self._command_handler.handle_chat_deletion(chat_id)
        elif chat_id.startswith('rename:'):
            return self._command_handler.handle_chat_rename(chat_id)
        elif chat_id.startswith('pin:') or chat_id.startswith('unpin:'):
            return self._command_handler.handle_chat_pinning(chat_id)
        else:
            return self._chat_ops_handler.handle_chat_switch(chat_id)
    
    # Методы-прокси для удобства
    def get_chat_list_data(self):
        return self.dispatch("get_chat_list_data")
    
    def handle_chat_selection(self, chat_id: str):
        return self.dispatch("handle_chat_selection", chat_id)
    
    def create_chat_with_js_handler(self):
        return self.dispatch("create_chat")
    
    async def send_message_stream_handler(self, prompt, chat_id, max_tokens, temperature, enable_thinking):
        async for result in self.dispatch("send_message_stream", prompt, chat_id, max_tokens, temperature, enable_thinking):
            yield result
    
    def init_app_handler(self):
        return self.dispatch("init_app")
    
    def stop_active_generation(self):
        return self.dispatch("stop_generation")