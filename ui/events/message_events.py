# ui/events/message_events.py
import gradio as gr
from handlers import ui_handlers
import asyncio

class MessageEvents:
    @staticmethod
    def clear_input_and_save_prompt(prompt):
        if prompt and prompt.strip():
            return "", prompt
        return "", ""
    
    @staticmethod
    def stop_generation():
        success = ui_handlers.stop_active_generation()
        if success:
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
    async def stream_response_only(saved_prompt, chat_id, max_tokens, temperature):
        if not saved_prompt or saved_prompt.strip() == "":
            yield [], chat_id or "", "[]", ""
            return
        try:
            async for history, _, dialog_id, chat_list_data, js_code in ui_handlers.send_message_stream_handler(
                saved_prompt, chat_id, max_tokens, temperature
            ):
                yield history, dialog_id, chat_list_data, js_code
        except asyncio.CancelledError:
            ui_handlers.stop_active_generation()
            try:
                from container import container
                dialog_service = container.get_dialog_service()
                current_dialog = dialog_service.get_current_dialog()
                history = current_dialog.to_ui_format() if current_dialog else []
                current_id = current_dialog.id if current_dialog else ""
                chat_list_data = ui_handlers.get_chat_list_data()
                yield history, current_id, chat_list_data, ""
            except Exception:
                yield [], "", "[]", ""
        except Exception:
            yield [], chat_id or "", "[]", ""
    
    @staticmethod
    def bind_message_events(submit_btn, stop_btn, user_input, current_dialog_id, chatbot,
                            max_tokens_slider, temperature_slider,
                            chat_list_data, generation_js_trigger):
        saved_prompt = gr.State()
        submit_btn.click(
            fn=MessageEvents.clear_input_and_save_prompt,
            inputs=[user_input],
            outputs=[user_input, saved_prompt]
        ).then(
            fn=MessageEvents.stream_response_only,
            inputs=[saved_prompt, current_dialog_id, max_tokens_slider, temperature_slider],
            outputs=[chatbot, current_dialog_id, chat_list_data, generation_js_trigger]
        )
        stop_btn.click(
            fn=MessageEvents.stop_generation,
            inputs=[],
            outputs=[generation_js_trigger]
        )
        user_input.submit(
            fn=MessageEvents.clear_input_and_save_prompt,
            inputs=[user_input],
            outputs=[user_input, saved_prompt]
        ).then(
            fn=MessageEvents.stream_response_only,
            inputs=[saved_prompt, current_dialog_id, max_tokens_slider, temperature_slider],
            outputs=[chatbot, current_dialog_id, chat_list_data, generation_js_trigger]
        )