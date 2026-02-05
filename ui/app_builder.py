# ui/app_builder.py
import gradio as gr
from ui.layouts.main_layout import create_main_layout
from ui.events import EventBinder

def create_app():
    """Создает приложение с привязанными событиями (всё в одном контексте)"""
    
    with gr.Blocks(title="Qwen3-30B Chat", fill_width=True) as demo:
        current_dialog_id = gr.State(value=None)
        
        # Создаем layout (теперь возвращаем 5 значений)
        sidebar_components, chatbot, user_input, submit_btn, stop_btn = create_main_layout()
        
        # Дополнительные компоненты
        chat_list_data = gr.Textbox(
            visible=False,
            elem_id="chat_list_data",
            interactive=False
        )
        
        js_trigger = gr.HTML(visible=False)
        
        # НОВЫЙ: Специальный триггер для JS событий генерации
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
            "chat_list_data": chat_list_data,
            "js_trigger": js_trigger,
            "generation_js_trigger": generation_js_trigger,  # <-- Новый триггер
            **sidebar_components
        }
        
        # Привязываем события ВНУТРИ контекста
        event_binder = EventBinder()
        event_binder.bind_all_events(demo, components, current_dialog_id)
        
        return demo