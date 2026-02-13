# ui/events/__init__.py
import gradio as gr
from .chat_events import ChatEvents
from .message_events import MessageEvents
from .generation_events import GenerationEvents
from handlers import ui_handlers

class EventBinder:
    def __init__(self):
        self.chat_events = ChatEvents()
        self.message_events = MessageEvents()
        self.generation_events = GenerationEvents()

    def bind_all_events(self, demo, components, current_dialog_id):
        self.chat_events.bind_chat_selection_events(
            components["chat_input"],
            components["chatbot"],
            current_dialog_id,
            components["chat_list_data"]
        )
        self.chat_events.bind_chat_creation_events(
            components["create_dialog_btn"],
            components["chatbot"],
            components["user_input"],
            current_dialog_id,
            components["js_trigger"],
            components["chat_list_data"]
        )
        # 👇 Кнопка настроек – без вызова Python, использует кэш из settings_data
        self.chat_events.bind_settings_button_events(
            components["settings_btn"],
            components["settings_data"]   # передаём компонент с настройками
        )
        self.message_events.bind_message_events(
            components["submit_btn"],
            components["stop_btn"],
            components["user_input"],
            current_dialog_id,
            components["chatbot"],
            components["chat_list_data"],
            components["generation_js_trigger"]
        )
        self.generation_events.bind_generation_js_events(
            components["generation_js_trigger"]
        )
        self.chat_events.bind_chat_list_update(components["chat_list_data"])

        # Инициализация: получаем историю, ID, список чатов И настройки
        demo.load(
            fn=ui_handlers.init_app_handler,
            outputs=[
                components["chatbot"],
                current_dialog_id,
                components["chat_list_data"],
                components["settings_data"]   # ← добавляем выход для настроек
            ]
        )