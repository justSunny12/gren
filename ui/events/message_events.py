# ui/events/message_events.py

import asyncio
import json
import time
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
    if (window.disableAutoScrollOnce) {
        window.disableAutoScrollOnce();
    }
    if (window.toggleGenerationButtons) {
        window.toggleGenerationButtons(false);
    }
</script>
"""


class MessageEvents:

    @staticmethod
    def clear_input_and_save_prompt(prompt: str) -> Tuple[str, Optional[str]]:
        if prompt and prompt.strip():
            return "", prompt
        return "", ""

    @staticmethod
    def save_and_show_user_message(prompt: str, chat_id: Optional[str]):
        """
        Сохраняет сообщение пользователя в диалог и возвращает обновлённую историю.
        При ошибке валидации возвращает тост и очищает saved_prompt.
        Возвращает 5 значений: (history, chat_id, chat_list_data, js_code, saved_prompt)
        """
        if not prompt or not prompt.strip():
            return [], chat_id or "", "[]", "", ""

        is_valid, error = validate_message(prompt)
        if not is_valid:
            dialog_service = container.get_dialog_service()
            current_dialog = dialog_service.get_current_dialog()
            history = current_dialog.to_ui_format() if current_dialog else []
            chat_list_data = ui_handlers.get_chat_list_data(scroll_target="today")

            timestamp = int(time.time() * 1000)
            error_escaped = json.dumps(error)
            js_toast = f"""
            <script>
            (function() {{
                var existing = document.getElementById('validation-toast');
                if (existing) existing.remove();

                var chat_container = document.querySelector('.chat-window-container');
                if (!chat_container) chat_container = document.body;

                var toast = document.createElement('div');
                toast.id = 'validation-toast';
                toast.className = 'validation-toast';
                toast.textContent = {error_escaped};
                chat_container.appendChild(toast);
                setTimeout(function() {{
                    if (toast.parentNode) toast.remove();
                }}, 5000);

                var ta = document.querySelector('.chat-input-wrapper textarea');
                if (ta) {{
                    ta.style.height = 'auto';
                    if (window.forceResizeTextarea) {{
                        setTimeout(window.forceResizeTextarea, 50);
                    }}
                }}
            }})();
            //{timestamp}
            </script>
            """
            # Возвращаем пустую строку для saved_prompt, чтобы следующий шаг не получил длинный промпт
            return history, chat_id or "", chat_list_data, js_toast, ""

        # Валидация пройдена
        dialog_service = container.get_dialog_service()
        if not chat_id:
            chat_id = dialog_service.create_dialog()

        dialog_service.add_message(chat_id, MessageRole.USER, prompt)

        dialog = dialog_service.get_dialog(chat_id)
        history = dialog.to_ui_format() if dialog else []
        chat_list_data = ui_handlers.get_chat_list_data(scroll_target="today")

        js_start = """
        <script>
            if (window.toggleGenerationButtons) {
                window.toggleGenerationButtons(true);
            }
        </script>
        """
        # В успешном случае возвращаем исходный prompt в saved_prompt
        return history, chat_id, chat_list_data, js_start, prompt

    @staticmethod
    async def stream_and_save_context(saved_prompt: str, chat_id: str):
        """
        Стримит ответ модели. Предполагает, что сообщение пользователя уже сохранено.
        Если saved_prompt пуст (ошибка валидации), ничего не делает.
        """
        if not saved_prompt or not chat_id:
            # Просто возвращаем текущую историю без изменений
            dialog_service = container.get_dialog_service()
            current_dialog = dialog_service.get_current_dialog()
            history = current_dialog.to_ui_format() if current_dialog else []
            chat_list_data = ui_handlers.get_chat_list_data()
            yield history, chat_id, chat_list_data, STOP_GENERATION_JS
            return

        logger = container.get_logger()
        dialog_service = container.get_dialog_service()
        config_service = container.get("config_service")
        user_config = user_config_service.get_user_config()
        gen_config = config_service.get_config().get("generation", {})

        max_tokens = user_config.generation.max_tokens or gen_config.get("default_max_tokens", 2048)
        temperature = user_config.generation.temperature or gen_config.get("default_temperature", 0.7)

        accumulated_response = ""
        try:
            async for history, _, dialog_id, chat_list_data, js_code in ui_handlers.send_message_stream_handler(
                saved_prompt, chat_id, max_tokens, temperature
            ):
                if history:
                    accumulated_response = history[-1]["content"] if history[-1]["role"] == "assistant" else ""
                yield history, dialog_id, chat_list_data, js_code
        except asyncio.CancelledError:
            ui_handlers.stop_active_generation()
        except Exception as error:
            traceback.print_exc()
            logger.error(f"Error in stream: {error}")
        finally:
            if accumulated_response:
                dialog = dialog_service.get_dialog(chat_id)
                if dialog:
                    try:
                        dialog.add_interaction_to_context(saved_prompt, accumulated_response)
                        dialog.save_context_state()
                    except Exception as ctx_err:
                        logger.warning(f"Ошибка обновления контекста: {ctx_err}")

            final_dialog = dialog_service.get_dialog(chat_id)
            final_history = final_dialog.to_ui_format() if final_dialog else []
            final_chat_list = ui_handlers.get_chat_list_data()
            js_stop = STOP_GENERATION_JS
            yield final_history, chat_id, final_chat_list, js_stop

    @staticmethod
    def stop_generation() -> str:
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
        saved_prompt = gr.State()

        def start_chain(trigger):
            trigger(
                fn=MessageEvents.clear_input_and_save_prompt,
                inputs=[user_input],
                outputs=[user_input, saved_prompt]
            ).then(
                fn=MessageEvents.save_and_show_user_message,
                inputs=[saved_prompt, current_dialog_id],
                outputs=[chatbot, current_dialog_id, chat_list_data, generation_js_trigger, saved_prompt]
            ).then(
                fn=MessageEvents.stream_and_save_context,
                inputs=[saved_prompt, current_dialog_id],
                outputs=[chatbot, current_dialog_id, chat_list_data, generation_js_trigger]
            )

        start_chain(submit_btn.click)
        start_chain(user_input.submit)

        stop_btn.click(
            fn=MessageEvents.stop_generation,
            inputs=[],
            outputs=[generation_js_trigger]
        )