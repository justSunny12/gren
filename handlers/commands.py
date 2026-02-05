# handlers/commands.py
import urllib.parse
from .base import BaseHandler

class CommandHandler(BaseHandler):
    """Обработчик команд из чатов (удаление, переименование, закрепление)"""
    
    def handle_chat_pinning(self, pin_command: str):
        """Обработчик закрепления/открепления чата"""
        try:
            parts = pin_command.split(':')
            if len(parts) != 3:
                return [], "", self.get_chat_list_data()
            
            action_type = parts[0]
            chat_id = parts[1]
            action = parts[2]
            
            if action_type != action:
                return [], "", self.get_chat_list_data()
            
            dialog = self.dialog_service.get_dialog(chat_id)
            if not dialog:
                return [], "", self.get_chat_list_data()
            
            if action == 'pin':
                success = self.dialog_service.pin_dialog(chat_id)
            else:  # unpin
                success = self.dialog_service.unpin_dialog(chat_id)
            
            updated_dialog = self.dialog_service.get_dialog(chat_id)
            
            if updated_dialog:
                history = updated_dialog.to_ui_format()
            else:
                history = []
            
            chat_list_data = self.get_chat_list_data()
            return history, chat_id, chat_list_data
            
        except Exception:
            return [], "", self.get_chat_list_data()
    
    def handle_chat_deletion(self, delete_command: str):
        """Обработчик удаления чата"""
        try:
            parts = delete_command.split(':')
            if len(parts) != 3 or parts[0] != 'delete':
                return [], "", self.get_chat_list_data()
            
            chat_id = parts[1]
            is_active = parts[2] == 'active'
            
            dialog_to_delete = self.dialog_service.get_dialog(chat_id)
            if not dialog_to_delete:
                return [], "", self.get_chat_list_data()
            
            current_before = self.dialog_service.get_current_dialog()
            current_id_before = current_before.id if current_before else None
            
            is_currently_active = (current_id_before == chat_id)
            keep_current = not is_currently_active
            
            success = self.dialog_service.delete_dialog(
                chat_id, 
                keep_current=keep_current
            )
            
            if not success:
                return [], "", self.get_chat_list_data()
            
            current_after = self.dialog_service.get_current_dialog()
            
            if current_after:
                history = current_after.to_ui_format()
                new_id = current_after.id
            else:
                history = []
                new_id = ""
            
            chat_list_data = self.get_chat_list_data()
            return history, new_id, chat_list_data
            
        except Exception:
            return [], "", self.get_chat_list_data()
    
    def handle_chat_rename(self, rename_command: str):
        """Обработчик переименования чата"""
        try:
            parts = rename_command.split(':', 2)
            if len(parts) != 3 or parts[0] != 'rename':
                return [], "", self.get_chat_list_data()
            
            chat_id = parts[1]
            new_name = urllib.parse.unquote(parts[2])
            
            dialog_to_rename = self.dialog_service.get_dialog(chat_id)
            if not dialog_to_rename:
                return [], "", self.get_chat_list_data()
            
            old_name = dialog_to_rename.name
            
            if not new_name or not new_name.strip():
                return [], "", self.get_chat_list_data()
            
            chat_naming_config = self.config.get("chat_naming", {})
            max_length = chat_naming_config.get("max_name_length", 50)
            if len(new_name) > max_length:
                new_name = new_name[:max_length]
            
            success = self.dialog_service.rename_dialog(chat_id, new_name)
            
            if not success:
                return [], "", self.get_chat_list_data()
            
            updated_dialog = self.dialog_service.get_dialog(chat_id)
            
            if updated_dialog:
                history = updated_dialog.to_ui_format()
            else:
                history = []
            
            chat_list_data = self.get_chat_list_data()
            return history, chat_id, chat_list_data
            
        except Exception:
            return [], "", self.get_chat_list_data()
    
    def get_chat_list_data(self):
        """Получает данные списка чатов (делегирует ChatListHandler)"""
        # Импортируем здесь, чтобы избежать циклических зависимостей
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data()