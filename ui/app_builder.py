# ui/app_builder.py
import gradio as gr
from ui.layouts.main_layout import create_main_layout
from ui.events import EventBinder

def create_app():
    """Создает приложение с привязанными событиями"""
    
    with gr.Blocks(title="Gren Chat", fill_width=True) as demo:
        current_dialog_id = gr.State(value=None)
        
        # Теперь получаем 8 значений
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
        
        # Дополнительные компоненты
        chat_list_data = gr.Textbox(
            visible=False,
            elem_id="chat_list_data",
            interactive=False
        )
        
        js_trigger = gr.HTML(visible=False)
        generation_js_trigger = gr.HTML(
            visible=False,
            elem_id="generation_js_trigger"
        )
        
        # Собираем все компоненты в словарь
        components = {
            "demo": demo,
            "current_dialog_id": current_dialog_id,
            "chatbot": chatbot,
            "user_input": user_input,
            "submit_btn": submit_btn,
            "stop_btn": stop_btn,
            "attach_btn": attach_btn,
            "thinking_btn": thinking_btn,      # <-- добавили
            "search_btn": search_btn,          # <-- добавили
            "settings_btn": settings_btn,
            "chat_list_data": chat_list_data,
            "js_trigger": js_trigger,
            "generation_js_trigger": generation_js_trigger,
            **sidebar_components
        }
        
        # Привязываем события
        event_binder = EventBinder()
        event_binder.bind_all_events(demo, components, current_dialog_id)
        
        return demo