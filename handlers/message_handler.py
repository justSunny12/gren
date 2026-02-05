# handlers/message_handler.py (исправленная версия)
from .base import BaseHandler

class MessageHandler(BaseHandler):
    """Обработчик сообщений"""
    
    def send_message_handler(self, prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Обработчик отправки сообщения"""
        try:
            if not prompt.strip():
                # Возвращаем 4 значения для совместимости с UI
                return [], "", chat_id or "", self.get_chat_list_data()

            if not chat_id:
                chat_id = self.dialog_service.create_dialog()

            history, _, new_chat_id = self.chat_service.process_message(
                prompt, chat_id, max_tokens, temperature, enable_thinking
            )

            chat_list_data = self.get_chat_list_data()
            
            # УБИРАЕМ chat_name из возвращаемых значений, так как в UI он не используется
            return history, "", new_chat_id, chat_list_data

        except Exception as e:
            print(f"❌ Ошибка в send_message_handler: {e}")
            # Возвращаем 4 значения для совместимости
            return [], "", chat_id or "", self.get_chat_list_data()
    
    def get_chat_list_data(self):
        """Получает данные списка чатов"""
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data()