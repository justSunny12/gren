# handlers/chat_operations.py
import json
from .base import BaseHandler

class ChatOperationsHandler(BaseHandler):
    """Обработчик операций с чатами (переключение, создание)"""
    
    def handle_chat_switch(self, chat_id: str):
        """Обрабатывает переключение на чат по ID (без команд) — скролл не нужен"""
        if not self.check_debounce():
            current_dialog = self.dialog_service.get_current_dialog()
            if current_dialog:
                history = current_dialog.to_ui_format()
                current_id = current_dialog.id
                chat_list_data = self.get_chat_list_data(scroll_target='none')
                return history, current_id, chat_list_data
            else:
                return [], "", self.get_chat_list_data(scroll_target='none')
        
        chat_id = chat_id.strip()
        if not chat_id or chat_id in ["null", "undefined"]:
            return [], "", self.get_chat_list_data(scroll_target='none')
        
        if self.dialog_service.switch_dialog(chat_id):
            dialog = self.dialog_service.get_dialog(chat_id)
            history = dialog.to_ui_format() if dialog else []
            chat_list_data = self.get_chat_list_data(scroll_target='none')
            return history, chat_id, chat_list_data
        else:
            return [], chat_id, self.get_chat_list_data(scroll_target='none')
    
    def create_chat_with_js_handler(self):
        """Создание нового чата — скролл к группе 'Сегодня'"""
        try:
            dialog_id = self.dialog_service.create_dialog()
            dialog = self.dialog_service.get_dialog(dialog_id)
            
            # Получаем обновлённые данные списка с флагом скролла к today
            chat_list_data = self.get_chat_list_data(scroll_target='today')
            
            history = dialog.to_ui_format()
            # Возвращаем пустой js_code, так как рендер произойдёт через chat_list_data.change
            return history, "", dialog_id, "", chat_list_data
            
        except Exception as e:
            self.logger.error("Ошибка при создании чата: %s", e)
            return [], "", None, "", "[]"