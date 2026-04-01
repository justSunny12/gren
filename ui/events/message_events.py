# ui/events/message_events.py

import asyncio
import json
import traceback
from typing import Optional, Tuple

import gradio as gr
from container import container
from handlers import ui_handlers
from models.enums import MessageRole
from services.chat.core import validate_message
from services.user_config_service import user_config_service

STOP_GENERATION_JS = """
<script>
    if (window.toggleGenerationButtons) {
        window.toggleGenerationButtons(false);
    }
</script>
"""


class MessageEvents:

    @staticmethod
    def clear_input_and_save_prompt(prompt: str) -> Tuple[str, Optional[str]]:
        """Очищает поле ввода и сохраняет текст в state."""
        if prompt and prompt.strip():
            return "", prompt
        return "", ""

    @staticmethod
    async def process_message(
        saved_prompt: str, chat_id: Optional[str]
    ):
        """
        Асинхронный генератор: валидация → сохранение → стриминг ответа.
        При ошибке валидации возвращает toast-уведомление и очищает saved_prompt.
        """
        logger = container.get_logger()
        logger.debug(f"process_message: saved_prompt length={len(saved_prompt) if saved_prompt else 0}")

        # Пустой ввод – просто возвращаем текущее состояние
        if not saved_prompt or not saved_prompt.strip():
            dialog_service = container.get_dialog_service()
            current_dialog = dialog_service.get_current_dialog()
            history = current_dialog.to_ui_format() if current_dialog else []
            chat_list_data = ui_handlers.get_chat_list_data()
            # Возвращаем пустую строку для saved_prompt, чтобы очистить state
            yield history, chat_id or "", chat_list_data, "", ""
            return

        # Валидация длины
        is_valid, error = validate_message(saved_prompt)
        if not is_valid:
            logger.warning(f"Validation failed: {error}")

            dialog_service = container.get_dialog_service()
            current_dialog = dialog_service.get_current_dialog()
            history = current_dialog.to_ui_format() if current_dialog else []
            chat_list_data = ui_handlers.get_chat_list_data()

            error_escaped = json.dumps(error)
            # Уникальный timestamp, чтобы Gradio считал JS новым
            timestamp = int(asyncio.get_event_loop().time() * 1000)
            js_toast = f"""
            <script>
            (function() {{
                // Удаляем предыдущий toast
                var existing = document.getElementById('validation-toast');
                if (existing) existing.remove();

                var toast = document.createElement('div');
                toast.id = 'validation-toast';
                toast.textContent = {error_escaped};
                toast.style.position = 'fixed';
                toast.style.top = '20px';
                toast.style.left = '50%';
                toast.style.transform = 'translateX(-50%)';
                toast.style.backgroundColor = '#FFF0F0';
                toast.style.color = '#D32F2F';
                toast.style.border = '1px solid #FFCDD2';
                toast.style.borderRadius = '8px';
                toast.style.padding = '12px 24px';
                toast.style.zIndex = '10000';
                toast.style.fontSize = '14px';
                toast.style.fontWeight = '500';
                toast.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
                toast.style.backdropFilter = 'blur(4px)';
                document.body.appendChild(toast);
                setTimeout(function() {{
                    if (toast.parentNode) toast.remove();
                }}, 3000);

                // Принудительный сброс высоты textarea
                var ta = document.querySelector('.chat-input-wrapper textarea');
                if (ta) {{
                    ta.style.height = 'auto';
                    if (window.forceResizeTextarea) {{
                        setTimeout(window.forceResizeTextarea, 50);
                    }}
                }}
            }})();
            // Добавляем мусор, чтобы код всегда считался новым
            //{timestamp}
            </script>
            """
            # Возвращаем пустую строку для saved_prompt, чтобы очистить state
            yield history, chat_id or "", chat_list_data, js_toast, ""
            return

        # Валидация пройдена – сохраняем сообщение пользователя
        dialog_service = container.get_dialog_service()
        if not chat_id:
            chat_id = dialog_service.create_dialog()
        dialog_service.add_message(chat_id, MessageRole.USER, saved_prompt)

        # Получаем обновлённую историю
        dialog = dialog_service.get_dialog(chat_id)
        history = dialog.to_ui_format() if dialog else []
        chat_list_data = ui_handlers.get_chat_list_data()

        # Включаем кнопку Stop
        js_start = """
        <script>
            if (window.toggleGenerationButtons) {
                window.toggleGenerationButtons(true);
            }
        </script>
        """
        # Возвращаем saved_prompt (он не очищается, чтобы стример его использовал)
        yield history, chat_id, chat_list_data, js_start, saved_prompt

        # Параметры генерации
        config_service = container.get("config_service")
        user_config = user_config_service.get_user_config()
        gen_config = config_service.get_config().get("generation", {})

        max_tokens = user_config.generation.max_tokens or gen_config.get("default_max_tokens", 2048)
        temperature = user_config.generation.temperature or gen_config.get("default_temperature", 0.7)

        # Стриминг ответа
        try:
            async for history, _, dialog_id, chat_list_data, js_code in ui_handlers.send_message_stream_handler(
                saved_prompt, chat_id, max_tokens, temperature
            ):
                # В стриме не нужно обновлять saved_prompt, передаём пустую строку
                yield history, dialog_id, chat_list_data, js_code, ""
        except asyncio.CancelledError:
            ui_handlers.stop_active_generation()
        except Exception as error:
            traceback.print_exc()
            logger.error(f"Error in stream: {error}")
        finally:
            final_dialog = dialog_service.get_dialog(chat_id)
            final_history = final_dialog.to_ui_format() if final_dialog else []
            final_chat_list = ui_handlers.get_chat_list_data()
            # Сначала стоп-сигнал — JS успевает снять pinned до обновления chatbot
            yield gr.update(), chat_id, gr.update(), STOP_GENERATION_JS, ""
            await asyncio.sleep(0.05)
            # Теперь обновляем историю — pinned уже false, скролла не будет
            yield final_history, chat_id, final_chat_list, gr.update(), ""

    @staticmethod
    def stop_generation() -> str:
        """Останавливает активную генерацию и возвращает JS-код."""
        success = ui_handlers.stop_active_generation()
        return STOP_GENERATION_JS if success else ""

    @staticmethod
    def bind_message_events(
        submit_btn,
        stop_btn,
        user_input,
        current_dialog_id,
        chatbot,
        chat_list_data,
        generation_js_trigger,
    ):
        # Один общий saved_prompt — обе цепочки используют одно состояние,
        # чтобы не было двух независимых State, гоняющихся за current_dialog_id
        saved_prompt = gr.State()

        def make_chain(trigger):
            trigger(
                fn=MessageEvents.clear_input_and_save_prompt,
                inputs=[user_input],
                outputs=[user_input, saved_prompt]
            ).then(
                fn=MessageEvents.process_message,
                inputs=[saved_prompt, current_dialog_id],
                outputs=[
                    chatbot,
                    current_dialog_id,
                    chat_list_data,
                    generation_js_trigger,
                    saved_prompt,
                ]
            )

        make_chain(submit_btn.click)
        make_chain(user_input.submit)

        stop_btn.click(
            fn=MessageEvents.stop_generation,
            inputs=[],
            outputs=[generation_js_trigger]
        )