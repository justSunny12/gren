# ui/events/message_events.py
from handlers import ui_handlers
import gradio as gr

class MessageEvents:
    """Обработчики событий сообщений"""
    
    @staticmethod
    def send_message(prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Обёртка для вызова обработчика сообщений (синхронный, для обратной совместимости)"""
        return ui_handlers.send_message_handler(
            prompt, chat_id, max_tokens, temperature, enable_thinking
        )
    
    @staticmethod
    async def stream_message(prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Асинхронный генератор для потоковой отправки сообщений"""
        async for history, _, dialog_id, chat_list_data in ui_handlers.send_message_stream_handler(
            prompt, chat_id, max_tokens, temperature, enable_thinking
        ):
            # history - обновленная история для chatbot
            # _ - пустая строка для user_input (очищаем поле ввода)
            # dialog_id - текущий ID диалога
            # chat_list_data - обновленный список чатов
            yield history, "", dialog_id, chat_list_data
    
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
        
        # Клик по кнопке отправки - используем асинхронный стриминг
        submit_btn.click(
            fn=MessageEvents.stream_message,
            inputs=message_inputs,
            outputs=message_outputs
        )
        
        # Отправка по Enter - также используем асинхронный стриминг
        user_input.submit(
            fn=MessageEvents.stream_message,
            inputs=message_inputs,
            outputs=message_outputs
        )