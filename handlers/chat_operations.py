# handlers/chat_operations.py
import json
from .base import BaseHandler

class ChatOperationsHandler(BaseHandler):
    """Обработчик операций с чатами (переключение, создание)"""
    
    def handle_chat_switch(self, chat_id: str):
        """Обрабатывает переключение на чат по ID (без команд)"""
        if not self.check_debounce():
            current_dialog = self.dialog_service.get_current_dialog()
            if current_dialog:
                history = current_dialog.to_ui_format()
                current_id = current_dialog.id
                chat_list_data = self.get_chat_list_data()
                return history, current_id, chat_list_data
            else:
                return [], "", self.get_chat_list_data()
        
        chat_id = chat_id.strip()
        
        if not chat_id or chat_id in ["null", "undefined"]:
            return [], "", self.get_chat_list_data()
        
        if self.dialog_service.switch_dialog(chat_id):
            dialog = self.dialog_service.get_dialog(chat_id)
            history = dialog.to_ui_format() if dialog else []
            chat_list_data = self.get_chat_list_data()
            return history, chat_id, chat_list_data
        else:
            return [], chat_id, self.get_chat_list_data()
    
    def create_chat_with_js_handler(self):
        """Обработчик создания нового чата"""
        try:
            dialog_id = self.dialog_service.create_dialog()
            dialog = self.dialog_service.get_dialog(dialog_id)
            
            chat_list_data = self.get_chat_list_data()
            
            js_code = """
            <script>
            document.dispatchEvent(new Event('chatListUpdated'));
            </script>
            """
            
            history = dialog.to_ui_format()
            
            return history, "", dialog_id, js_code, chat_list_data
            
        except Exception:
            return [], "", None, "", "[]"
    
    def get_chat_list_data(self):
        """Получает данные списка чатов (делегирует ChatListHandler)"""
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data()