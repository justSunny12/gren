# ui/app_builder.py
import gradio as gr
from ui.layouts.main_layout import create_main_layout
from ui.events import EventBinder

def create_app():
    with gr.Blocks(title="Gren Chat", fill_width=True) as demo:
        current_dialog_id = gr.State(value=None)

        (
            sidebar_components,
            chatbot,
            user_input,
            submit_btn,
            stop_btn,
            attach_btn,
            thinking_btn,
            search_btn,
            settings_btn
        ) = create_main_layout()

        create_dialog_btn = sidebar_components["create_dialog_btn"]
        chat_input = sidebar_components["chat_input"]
        settings_data = sidebar_components["settings_data"]   # ← добавили
        js_trigger = sidebar_components["js_trigger"]
        generation_js_trigger = sidebar_components["generation_js_trigger"]

        chat_list_data = gr.Textbox(
            visible=False,
            elem_id="chat_list_data",
            interactive=False
        )

        components = {
            "demo": demo,
            "current_dialog_id": current_dialog_id,
            "chatbot": chatbot,
            "user_input": user_input,
            "submit_btn": submit_btn,
            "stop_btn": stop_btn,
            "attach_btn": attach_btn,
            "thinking_btn": thinking_btn,
            "search_btn": search_btn,
            "settings_btn": settings_btn,
            "create_dialog_btn": create_dialog_btn,
            "chat_input": chat_input,
            "settings_data": settings_data,          # ← добавили
            "chat_list_data": chat_list_data,
            "js_trigger": js_trigger,
            "generation_js_trigger": generation_js_trigger,
        }

        event_binder = EventBinder()
        event_binder.bind_all_events(demo, components, current_dialog_id)

        return demo