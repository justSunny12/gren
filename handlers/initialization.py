# handlers/initialization.py
from .base import BaseHandler


class InitializationHandler(BaseHandler):
    """Обработчик инициализации приложения."""

    def init_app_handler(self):
        try:
            if not self.dialog_service.dialogs:
                chat_id = self.dialog_service.create_dialog()
            else:
                chat_id = self.dialog_service.current_dialog_id

            dialog = self.dialog_service.get_dialog(chat_id)
            history = dialog.to_ui_format() if dialog else []
            chat_list_data = self.get_chat_list_data(scroll_target='top')

            from handlers.mediator import _build_settings_json
            settings_json = _build_settings_json()

            return history, chat_id, chat_list_data, settings_json

        except Exception as e:
            self.logger.error("Ошибка в init_app_handler: %s", e)
            import json
            default_settings = {
                "current_max_tokens": 2048,
                "current_temperature": 0.7,
                "default_max_tokens": 2048,
                "default_temperature": 0.7,
                "min_max_tokens": 64,
                "max_max_tokens": 4096,
                "step_max_tokens": 64,
                "min_temperature": 0.1,
                "max_temperature": 1.5,
                "step_temperature": 0.05,
            }
            return [], None, "[]", json.dumps(default_settings, ensure_ascii=False)
