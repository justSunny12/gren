# handlers/__init__.py (ИСПРАВЛЕННАЯ ВЕРСИЯ)
from .commands import CommandHandler
from .chat_operations import ChatOperationsHandler
from .chat_list import ChatListHandler
from .message_handler import MessageHandler
from .initialization import InitializationHandler
from .naming_utils import NamingUtils

class UIHandlers:
    """Главный фасад для всех обработчиков UI"""
    
    def __init__(self):
        self._command_handler = CommandHandler()
        self._chat_ops_handler = ChatOperationsHandler()
        self._chat_list_handler = ChatListHandler()
        self._init_handler = InitializationHandler()
        self._naming_utils = NamingUtils()
        self.message_handler = MessageHandler()
    
    def get_chat_list_data(self):
        """Возвращает данные списка чатов с группировкой"""
        return self._chat_list_handler.get_chat_list_data()
    
    def handle_chat_selection(self, chat_id: str):
        """Обработчик выбора чата из списка"""
        if chat_id and chat_id.startswith('delete:'):
            return self._command_handler.handle_chat_deletion(chat_id)
        
        if chat_id and chat_id.startswith('rename:'):
            return self._command_handler.handle_chat_rename(chat_id)
        
        if chat_id and (chat_id.startswith('pin:') or chat_id.startswith('unpin:')):
            return self._command_handler.handle_chat_pinning(chat_id)
        
        return self._chat_ops_handler.handle_chat_switch(chat_id)
    
    def handle_chat_pinning(self, pin_command: str):
        """Обработчик закрепления/открепления чата"""
        return self._command_handler.handle_chat_pinning(pin_command)
    
    def handle_chat_deletion(self, delete_command: str):
        """Обработчик удаления чата"""
        return self._command_handler.handle_chat_deletion(delete_command)
    
    def handle_chat_rename(self, rename_command: str):
        """Обработчик переименования чата"""
        return self._command_handler.handle_chat_rename(rename_command)
    
    def create_chat_with_js_handler(self):
        """Обработчик создания нового чата"""
        return self._chat_ops_handler.create_chat_with_js_handler()
    
    async def send_message_stream_handler(self, prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Асинхронный обработчик для потоковой генерации"""
        # ВАЖНО: Это должен быть асинхронный генератор, а не обычный async метод
        async for result in self.message_handler.send_message_stream_handler(
            prompt, chat_id, max_tokens, temperature, enable_thinking
        ):
            yield result
    
    def init_app_handler(self):
        """Обработчик инициализации приложения"""
        return self._init_handler.init_app_handler()
    
    def stop_active_generation(self):
        """Останавливает активную генерацию сообщения"""
        return self.message_handler.stop_active_generation()

# Глобальный экземпляр для обратной совместимости
ui_handlers = UIHandlers()