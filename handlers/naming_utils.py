# handlers/naming_utils.py
from .base import BaseHandler

class NamingUtils(BaseHandler):
    """Утилиты для работы с названиями и настройками"""
    
    def get_chat_name_from_id(self, dialog_id: str) -> str:
        """Получает название чата по ID"""
        if not dialog_id:
            return "Чат"
        
        dialog = self.dialog_service.get_dialog(dialog_id)
        if dialog:
            chat_name = dialog.name.replace('\n', ' ').replace('\r', ' ')
            chat_name = ' '.join(chat_name.split())
            if len(chat_name) > 30:
                chat_name = chat_name[:27] + '...'
            return chat_name
        return "Чат"
    
    def load_user_settings(self):
        """Загружает пользовательские настройки"""
        try:
            generation_config = self.config.get("generation", {})
            return (
                generation_config.get("default_max_tokens", 512),
                generation_config.get("default_temperature", 0.7),
                generation_config.get("default_enable_thinking", False)
            )
        except Exception:
            default_config = self.config_service.get_default_config()
            generation_config = default_config.get("generation", {})
            return (
                generation_config.get("default_max_tokens", 512),
                generation_config.get("default_temperature", 0.7),
                generation_config.get("default_enable_thinking", False)
            )