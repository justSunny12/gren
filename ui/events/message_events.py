# ui/events/message_events.py
import gradio as gr
from handlers import ui_handlers

class MessageEvents:
    """Обработчики событий сообщений"""
    
    @staticmethod
    def send_message(prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Синхронный обработчик для обратной совместимости"""
        return ui_handlers.send_message_handler(
            prompt, chat_id, max_tokens, temperature, enable_thinking
        )
    
    @staticmethod
    def clear_input_and_save_prompt(prompt):
        """Очищает поле ввода и возвращает сохраненный промпт"""
        print(f"💾 Сохраняю промпт: '{prompt}'")
        return "", prompt  # Очищаем поле ввода, но сохраняем промпт
    
    @staticmethod
    async def stream_response_only(saved_prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Асинхронный генератор для обновления чатбота, использует сохраненный промпт"""
        if not saved_prompt or saved_prompt.strip() == "":
            yield [], chat_id, "[]"
            return
        
        print(f"🚀 Начинаю стриминг для промпта: '{saved_prompt}'")
        
        try:
            async for history, _, dialog_id, chat_list_data in ui_handlers.send_message_stream_handler(
                saved_prompt, chat_id, max_tokens, temperature, enable_thinking
            ):
                
                yield history, dialog_id, chat_list_data
            
        except Exception as e:
            print(f"❌ Ошибка в stream_response_only: {e}")
            import traceback
            traceback.print_exc()
            yield [], chat_id, "[]"
    
    @staticmethod
    def bind_message_events(submit_btn, user_input, current_dialog_id, chatbot, 
                            max_tokens_slider, temperature_slider, enable_thinking_checkbox,
                            chat_list_data):
        """Привязывает события отправки сообщений"""
        
        # Создаем состояние для сохранения промпта
        saved_prompt = gr.State()
        
        # Цепочка событий:
        # 1. clear_input_and_save_prompt: очищает поле ввода, сохраняет промпт в состояние
        # 2. stream_response_only: использует сохраненный промпт из состояния
        
        # Для кнопки отправки
        submit_btn.click(
            fn=MessageEvents.clear_input_and_save_prompt,
            inputs=[user_input],
            outputs=[user_input, saved_prompt]  # Очищаем поле ввода и сохраняем промпт
        ).then(
            fn=MessageEvents.stream_response_only,
            inputs=[saved_prompt, current_dialog_id, max_tokens_slider, temperature_slider, enable_thinking_checkbox],
            outputs=[chatbot, current_dialog_id, chat_list_data]
        )
        
        # Для отправки по Enter
        user_input.submit(
            fn=MessageEvents.clear_input_and_save_prompt,
            inputs=[user_input],
            outputs=[user_input, saved_prompt]
        ).then(
            fn=MessageEvents.stream_response_only,
            inputs=[saved_prompt, current_dialog_id, max_tokens_slider, temperature_slider, enable_thinking_checkbox],
            outputs=[chatbot, current_dialog_id, chat_list_data]
        )