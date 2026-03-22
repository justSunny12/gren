# handlers/commands.py
import urllib.parse
import json
from .base import BaseHandler
from services.user_config_service import user_config_service


class CommandHandler(BaseHandler):
    """Обработчик команд из чатов (удаление, переименование, закрепление, мышление, настройки)"""

    # ──────────────────────────────────────────────
    # Приватные хелперы
    # ──────────────────────────────────────────────

    def _current_history_and_id(self):
        """Возвращает (history, id) текущего диалога."""
        dialog = self.dialog_service.get_current_dialog()
        return (dialog.to_ui_format(), dialog.id) if dialog else ([], "")

    def _error_response(self, scroll_target: str = 'none'):
        return [], "", self.get_chat_list_data(scroll_target=scroll_target)

    def _toggle_bool_setting(self, patch: dict) -> tuple:
        """
        Универсальный тоггл булевого флага в user_config.
        patch — {"generation": {"enable_thinking": None}} или {"search_enabled": None}.
        None-значение является маркером «инвертировать текущее».
        """
        try:
            user_config = user_config_service.get_user_config(force_reload=True)

            if "generation" in patch:
                key = next(iter(patch["generation"]))
                current = getattr(user_config.generation, key, None) or False
                patch["generation"][key] = not current
            else:
                key = next(iter(patch))
                current = getattr(user_config, key, None) or False
                patch[key] = not current

            self.config_service.update_user_settings_batch(patch)
            return None, "", self.get_chat_list_data(scroll_target='none')

        except Exception as e:
            self.logger.error("Ошибка в _toggle_bool_setting: %s", e)
            return None, "", self.get_chat_list_data(scroll_target='none')

    # ──────────────────────────────────────────────
    # Публичные обработчики
    # ──────────────────────────────────────────────

    def handle_chat_pinning(self, pin_command: str):
        try:
            parts = pin_command.split(':')
            if len(parts) != 3 or parts[0] != parts[2]:
                return self._error_response()
            action, chat_id = parts[0], parts[1]
            if not self.dialog_service.get_dialog(chat_id):
                return self._error_response()

            if action == 'pin':
                self.dialog_service.pin_dialog(chat_id)
                scroll_target = 'top'
            else:
                self.dialog_service.unpin_dialog(chat_id)
                scroll_target = 'none'

            dialog = self.dialog_service.get_dialog(chat_id)
            history = dialog.to_ui_format() if dialog else []
            return history, chat_id, self.get_chat_list_data(scroll_target=scroll_target)
        except Exception:
            return self._error_response()

    def handle_chat_deletion(self, delete_command: str):
        try:
            parts = delete_command.split(':')
            if len(parts) != 3 or parts[0] != 'delete':
                return self._error_response()
            chat_id = parts[1]

            if not self.dialog_service.get_dialog(chat_id):
                return self._error_response()

            current_before = self.dialog_service.get_current_dialog()
            keep_current = not (current_before and current_before.id == chat_id)

            if not self.dialog_service.delete_dialog(chat_id, keep_current=keep_current):
                return self._error_response()

            history, new_id = self._current_history_and_id()
            return history, new_id, self.get_chat_list_data(scroll_target='none')
        except Exception:
            return self._error_response()

    def handle_chat_rename(self, rename_command: str):
        try:
            parts = rename_command.split(':', 2)
            if len(parts) != 3 or parts[0] != 'rename':
                return self._error_response()
            chat_id, new_name = parts[1], urllib.parse.unquote(parts[2])

            if not self.dialog_service.get_dialog(chat_id):
                return self._error_response()
            if not new_name or not new_name.strip():
                return self._error_response()

            max_length = self.config.get("chat_naming", {}).get("max_name_length", 50)
            new_name = new_name[:max_length]

            if not self.dialog_service.rename_dialog(chat_id, new_name):
                return self._error_response()

            dialog = self.dialog_service.get_dialog(chat_id)
            history = dialog.to_ui_format() if dialog else []
            return history, chat_id, self.get_chat_list_data(scroll_target='none')
        except Exception:
            return self._error_response()

    def handle_thinking_toggle(self, command: str):
        return self._toggle_bool_setting({"generation": {"enable_thinking": None}})

    def handle_search_toggle(self, command: str):
        return self._toggle_bool_setting({"search_enabled": None})

    def handle_settings_apply(self, command: str):
        """Формат: settings:apply:{"max_tokens":2048,"temperature":0.8}"""
        try:
            parts = command.split(':', 2)
            if len(parts) != 3 or parts[0] != 'settings' or parts[1] != 'apply':
                history, chat_id = self._current_history_and_id()
                return history, chat_id, self.get_chat_list_data(scroll_target='none')

            settings = json.loads(parts[2])
            update_data = {k: settings[k] for k in ('max_tokens', 'temperature') if k in settings}

            if update_data:
                if self.config_service.update_user_settings_batch({"generation": update_data}):
                    user_config_service.invalidate_cache()

            history, chat_id = self._current_history_and_id()
            return history, chat_id, self.get_chat_list_data(scroll_target='none')

        except Exception as e:
            self.logger.error("Ошибка в handle_settings_apply: %s", e)
            history, chat_id = self._current_history_and_id()
            return history, chat_id, self.get_chat_list_data(scroll_target='none')
