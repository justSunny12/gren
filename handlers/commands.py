# handlers/commands.py
import urllib.parse
import json
from .base import BaseHandler
from services.user_config_service import user_config_service

class CommandHandler(BaseHandler):
    """Обработчик команд из чатов (удаление, переименование, закрепление, мышление, настройки)"""
    
    def handle_chat_pinning(self, pin_command: str):
        try:
            parts = pin_command.split(':')
            if len(parts) != 3:
                return [], "", self.get_chat_list_data(scroll_target='none')
            action_type = parts[0]
            chat_id = parts[1]
            action = parts[2]
            if action_type != action:
                return [], "", self.get_chat_list_data(scroll_target='none')
            dialog = self.dialog_service.get_dialog(chat_id)
            if not dialog:
                return [], "", self.get_chat_list_data(scroll_target='none')
            if action == 'pin':
                success = self.dialog_service.pin_dialog(chat_id)
                scroll_target = 'top'
            else:
                success = self.dialog_service.unpin_dialog(chat_id)
                scroll_target = 'none'
            updated_dialog = self.dialog_service.get_dialog(chat_id)
            history = updated_dialog.to_ui_format() if updated_dialog else []
            chat_list_data = self.get_chat_list_data(scroll_target=scroll_target)
            return history, chat_id, chat_list_data
        except Exception:
            return [], "", self.get_chat_list_data(scroll_target='none')
    
    def handle_chat_deletion(self, delete_command: str):
        try:
            parts = delete_command.split(':')
            if len(parts) != 3 or parts[0] != 'delete':
                return [], "", self.get_chat_list_data(scroll_target='none')
            chat_id = parts[1]
            is_active = parts[2] == 'active'
            dialog_to_delete = self.dialog_service.get_dialog(chat_id)
            if not dialog_to_delete:
                return [], "", self.get_chat_list_data(scroll_target='none')
            current_before = self.dialog_service.get_current_dialog()
            current_id_before = current_before.id if current_before else None
            is_currently_active = (current_id_before == chat_id)
            keep_current = not is_currently_active
            success = self.dialog_service.delete_dialog(chat_id, keep_current=keep_current)
            if not success:
                return [], "", self.get_chat_list_data(scroll_target='none')
            current_after = self.dialog_service.get_current_dialog()
            if current_after:
                history = current_after.to_ui_format()
                new_id = current_after.id
            else:
                history = []
                new_id = ""
            chat_list_data = self.get_chat_list_data(scroll_target='none')
            return history, new_id, chat_list_data
        except Exception:
            return [], "", self.get_chat_list_data(scroll_target='none')
    
    def handle_chat_rename(self, rename_command: str):
        try:
            parts = rename_command.split(':', 2)
            if len(parts) != 3 or parts[0] != 'rename':
                return [], "", self.get_chat_list_data(scroll_target='none')
            chat_id = parts[1]
            new_name = urllib.parse.unquote(parts[2])
            dialog_to_rename = self.dialog_service.get_dialog(chat_id)
            if not dialog_to_rename:
                return [], "", self.get_chat_list_data(scroll_target='none')
            if not new_name or not new_name.strip():
                return [], "", self.get_chat_list_data(scroll_target='none')
            chat_naming_config = self.config.get("chat_naming", {})
            max_length = chat_naming_config.get("max_name_length", 50)
            if len(new_name) > max_length:
                new_name = new_name[:max_length]
            success = self.dialog_service.rename_dialog(chat_id, new_name)
            if not success:
                return [], "", self.get_chat_list_data(scroll_target='none')
            updated_dialog = self.dialog_service.get_dialog(chat_id)
            history = updated_dialog.to_ui_format() if updated_dialog else []
            chat_list_data = self.get_chat_list_data(scroll_target='none')
            return history, chat_id, chat_list_data
        except Exception:
            return [], "", self.get_chat_list_data(scroll_target='none')
    
    def handle_thinking_toggle(self, command: str):
        try:
            user_config_service.invalidate_cache()
            user_config = user_config_service.get_user_config()
            current = user_config.generation.enable_thinking
            if current is None:
                current = False
            new_state = not current

            success = self.config_service.update_user_settings_batch({
                "generation": {"enable_thinking": new_state}
            })
            if not success:
                return None, "", self.get_chat_list_data(scroll_target='none')

            self._config = None
            user_config_service.invalidate_cache()
            chat_list_data = self.get_chat_list_data(scroll_target='none')
            return None, "", chat_list_data
        except Exception as e:
            self.logger.error("Ошибка в handle_thinking_toggle")
            return None, "", self.get_chat_list_data(scroll_target='none')
    
    def handle_search_toggle(self, command: str):
        try:
            user_config_service.invalidate_cache()
            user_config = user_config_service.get_user_config()
            current = user_config.search_enabled
            if current is None:
                current = False
            new_state = not current

            success = self.config_service.update_user_settings_batch({
                "search_enabled": new_state
            })
            if not success:
                return None, "", self.get_chat_list_data(scroll_target='none')

            self._config = None
            user_config_service.invalidate_cache()
            chat_list_data = self.get_chat_list_data(scroll_target='none')
            return None, "", chat_list_data
        except Exception as e:
            self.logger.error("Ошибка в handle_search_toggle")
            return None, "", self.get_chat_list_data(scroll_target='none')
    
    def handle_settings_apply(self, command: str):
        """
        Формат: settings:apply:{"max_tokens":2048,"temperature":0.8}
        """
        try:
            parts = command.split(':', 2)
            if len(parts) != 3 or parts[0] != 'settings' or parts[1] != 'apply':
                current_dialog = self.dialog_service.get_current_dialog()
                history = current_dialog.to_ui_format() if current_dialog else []
                chat_id = current_dialog.id if current_dialog else ""
                return history, chat_id, self.get_chat_list_data(scroll_target='none')

            settings_str = parts[2]
            settings = json.loads(settings_str)

            max_tokens = settings.get("max_tokens")
            temperature = settings.get("temperature")

            update_data = {}
            if max_tokens is not None:
                update_data["max_tokens"] = max_tokens
            if temperature is not None:
                update_data["temperature"] = temperature

            if not update_data:
                current_dialog = self.dialog_service.get_current_dialog()
                history = current_dialog.to_ui_format() if current_dialog else []
                chat_id = current_dialog.id if current_dialog else ""
                return history, chat_id, self.get_chat_list_data(scroll_target='none')

            success = self.config_service.update_user_settings_batch({
                "generation": update_data
            })

            if success:
                user_config_service.invalidate_cache()
                self._config = None

            current_dialog = self.dialog_service.get_current_dialog()
            if current_dialog:
                history = current_dialog.to_ui_format()
                chat_id = current_dialog.id
            else:
                history = []
                chat_id = ""

            chat_list_data = self.get_chat_list_data(scroll_target='none')
            return history, chat_id, chat_list_data

        except Exception as e:
            self.logger.error("Ошибка в handle_settings_apply: %s", e)
            current_dialog = self.dialog_service.get_current_dialog()
            history = current_dialog.to_ui_format() if current_dialog else []
            chat_id = current_dialog.id if current_dialog else ""
            return history, chat_id, self.get_chat_list_data(scroll_target='none')