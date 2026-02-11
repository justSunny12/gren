# ui/events/message_events.py (упрощенная рабочая версия)
import gradio as gr
from handlers import ui_handlers

class MessageEvents:
    """Обработчики событий сообщений"""
    
    @staticmethod
    def clear_input_and_save_prompt(prompt):
        """Очищает поле ввода и возвращает сохраненный промпт"""
        if prompt and prompt.strip():
            return "", prompt  # Очищаем поле ввода, но сохраняем промпт
        return "", ""
    
    @staticmethod
    def stop_generation():
        """Останавливает генерацию через обработчик"""
        success = ui_handlers.stop_active_generation()
        if success:
            # print("✅ Генерация остановлена по запросу пользователя")
            
            # Возвращаем JS код для немедленного переключения кнопок
            js_code = """
            <script>
            if (window.toggleGenerationButtons) {
                window.toggleGenerationButtons(false);
            }
            </script>
            """
            return js_code
        
        return ""
    
    @staticmethod
    async def stream_response_only(saved_prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Асинхронный генератор для обновления чатбота, использует сохраненный промпт"""
        if not saved_prompt or saved_prompt.strip() == "":
            yield [], chat_id, "[]", ""
            return
                
        try:
            async for history, _, dialog_id, chat_list_data, js_code in ui_handlers.send_message_stream_handler(
                saved_prompt, chat_id, max_tokens, temperature, enable_thinking
            ):
                yield history, dialog_id, chat_list_data, js_code  # 4 значения, включая js_code
            
        except Exception as e:
            print(f"❌ Ошибка в stream_response_only: {e}")
            import traceback
            traceback.print_exc()
            yield [], chat_id, "[]", ""
    
    @staticmethod
    def bind_message_events(submit_btn, stop_btn, user_input, current_dialog_id, chatbot, 
                            max_tokens_slider, temperature_slider, enable_thinking_checkbox,
                            chat_list_data, generation_js_trigger):  # <-- Новый параметр
        """Привязывает события отправки сообщений"""
        
        # Создаем состояние для сохранения промпта
        saved_prompt = gr.State()
        
        # ========== ЦЕПОЧКА ДЛЯ КНОПКИ ОТПРАВКИ ==========
        # Оригинальная рабочая цепочка
        submit_btn.click(
            fn=MessageEvents.clear_input_and_save_prompt,
            inputs=[user_input],
            outputs=[user_input, saved_prompt]
        ).then(
            fn=MessageEvents.stream_response_only,
            inputs=[saved_prompt, current_dialog_id, max_tokens_slider, temperature_slider, enable_thinking_checkbox],
            outputs=[chatbot, current_dialog_id, chat_list_data, generation_js_trigger]  # <-- 4 выхода
        )
        
        # ========== ЦЕПОЧКА ДЛЯ КНОПКИ ОСТАНОВКИ ==========
        # Останавливаем генерацию и возвращаем JS код
        stop_btn.click(
            fn=MessageEvents.stop_generation,
            inputs=[],
            outputs=[generation_js_trigger]  # <-- Возвращаем JS код
        )
        
        # ========== ЦЕПОЧКА ДЛЯ ОТПРАВКИ ПО ENTER ==========
        user_input.submit(
            fn=MessageEvents.clear_input_and_save_prompt,
            inputs=[user_input],
            outputs=[user_input, saved_prompt]
        ).then(
            fn=MessageEvents.stream_response_only,
            inputs=[saved_prompt, current_dialog_id, max_tokens_slider, temperature_slider, enable_thinking_checkbox],
            outputs=[chatbot, current_dialog_id, chat_list_data, generation_js_trigger]  # <-- 4 выхода
        )