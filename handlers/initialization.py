# handlers/initialization.py
import json
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

            settings_data = {
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
            settings_json = json.dumps(settings_data, ensure_ascii=False)

            return history, chat_id, chat_list_data, settings_json

        except Exception as e:
            self.logger.error("Ошибка в init_app_handler: %s", e)
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
                "step_temperature": 0.05
            }
            return [], None, "[]", json.dumps(default_settings, ensure_ascii=False)