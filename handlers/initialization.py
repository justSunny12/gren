# handlers/initialization.py
from .base import BaseHandler

class InitializationHandler(BaseHandler):
    """Обработчик инициализации приложения"""
    
    def init_app_handler(self):
        try:
            if not self.dialog_service.dialogs:
                chat_id = self.dialog_service.create_dialog()
            else:
                chat_id = self.dialog_service.current_dialog_id

            dialog = self.dialog_service.get_dialog(chat_id)
            history = dialog.to_ui_format() if dialog else []
                
            # Инициализация — скролл в самый верх
            chat_list_data = self.get_chat_list_data(scroll_target='top')
            
            generation_config = self.config.get("generation", {})
            max_tokens = generation_config.get("default_max_tokens", 512)
            temperature = generation_config.get("default_temperature", 0.7)

            # enable_thinking больше не возвращаем
            return history, chat_id, max_tokens, temperature, chat_list_data

        except Exception as e:
            print(f"❌ Ошибка в init_app_handler: {e}")
            default_config = self.config_service.get_default_config()
            generation_config = default_config.get("generation", {})
            return [], None, \
                   generation_config.get("default_max_tokens", 512), \
                   generation_config.get("default_temperature", 0.7), \
                   "[]"
        
    def get_chat_list_data(self, scroll_target: str = 'none'):
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data(scroll_target=scroll_target)