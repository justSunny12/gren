# ui/events/__init__.py
import gradio as gr
from .chat_events import ChatEvents
from .sidebar_events import SidebarEvents
from .message_events import MessageEvents
from handlers import ui_handlers

class EventBinder:
    """Агрегатор для привязки всех событий"""
    
    def __init__(self):
        self.chat_events = ChatEvents()
        self.sidebar_events = SidebarEvents()
        self.message_events = MessageEvents()
    
    def bind_all_events(self, demo, components, current_dialog_id):
        """Привязывает все события к интерфейсу"""
        
        # 1. События чата
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
        
        # 2. События сайдбара
        self.sidebar_events.bind_settings_events(
            components["max_tokens"],
            components["temperature"],
            components["enable_thinking"],
            components["reset_settings_btn"]
        )
        
        # 3. События сообщений
        self.message_events.bind_message_events(
            components["submit_btn"],
            components["user_input"],
            current_dialog_id,
            components["chatbot"],
            components["max_tokens"],
            components["temperature"],
            components["enable_thinking"],
            components["chat_list_data"]
        )
        
        # 4. Инициализация приложения
        demo.load(
            fn=ui_handlers.init_app_handler,
            outputs=[
                components["chatbot"],
                current_dialog_id,
                components["max_tokens"],
                components["temperature"],
                components["enable_thinking"],
                components["chat_list_data"]
            ]
        )
        
        # 5. Обновление списка чатов через JS
        self.chat_events.bind_chat_list_update(components["chat_list_data"])