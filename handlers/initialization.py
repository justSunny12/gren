# handlers/initialization.py (исправленная версия)
from .base import BaseHandler

class InitializationHandler(BaseHandler):
    """Обработчик инициализации приложения"""
    
    def init_app_handler(self):
        """Обработчик инициализации приложения"""
        try:
            if not self.dialog_service.dialogs:
                chat_id = self.dialog_service.create_dialog()
            else:
                chat_id = self.dialog_service.current_dialog_id

            # ИСПРАВЛЕНИЕ: используем dialog_service вместо chat_service
            dialog = self.dialog_service.get_dialog(chat_id)
            if dialog:
                history = dialog.to_ui_format()
            else:
                history = []
                
            chat_list_data = self.get_chat_list_data()
            
            generation_config = self.config.get("generation", {})
            max_tokens = generation_config.get("default_max_tokens", 512)
            temperature = generation_config.get("default_temperature", 0.7)
            enable_thinking = generation_config.get("default_enable_thinking", False)

            return history, chat_id, max_tokens, temperature, enable_thinking, chat_list_data

        except Exception as e:
            print(f"❌ Ошибка в init_app_handler: {e}")
            default_config = self.config_service.get_default_config()
            generation_config = default_config.get("generation", {})
            return [], None, generation_config.get("default_max_tokens", 512), generation_config.get("default_temperature", 0.7), generation_config.get("default_enable_thinking", False), "[]"
        
    def get_chat_list_data(self):
        """Получает данные списка чатов"""
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data()