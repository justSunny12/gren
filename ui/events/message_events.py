# ui/events/message_events.py
from handlers import ui_handlers

class MessageEvents:
    """Обработчики событий сообщений"""
    
    @staticmethod
    def send_message(prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Обёртка для вызова обработчика сообщений"""
        return ui_handlers.send_message_handler(
            prompt, chat_id, max_tokens, temperature, enable_thinking
        )
    
    @staticmethod
    def bind_message_events(submit_btn, user_input, current_dialog_id, chatbot, 
                            max_tokens_slider, temperature_slider, enable_thinking_checkbox,
                            chat_list_data):
        """Привязывает события отправки сообщений"""
        message_inputs = [
            user_input, 
            current_dialog_id,
            max_tokens_slider,
            temperature_slider,
            enable_thinking_checkbox
        ]
        
        message_outputs = [
            chatbot,
            user_input,
            current_dialog_id,
            chat_list_data
        ]
        
        # Клик по кнопке отправки
        submit_btn.click(
            fn=MessageEvents.send_message,
            inputs=message_inputs,
            outputs=message_outputs
        )
        
        # Отправка по Enter
        user_input.submit(
            fn=MessageEvents.send_message,
            inputs=message_inputs,
            outputs=message_outputs
        )