# /ui/components/buttons.py
import gradio as gr
from container import container

class ButtonComponents:
    """Фабрика кнопок с использованием конфигов"""
    
    def __init__(self):
        self.config = container.get_config().get("ui", {})
    
    def create_primary_button(self, text: str, **kwargs) -> gr.Button:
        """Создает основную кнопку"""
        return gr.Button(
            text,
            variant="primary",
            elem_classes="primary-btn",
            **kwargs
        )
    
    def create_secondary_button(self, text: str, **kwargs) -> gr.Button:
        """Создает второстепенную кнопку"""
        return gr.Button(
            text,
            variant="secondary",
            elem_classes="secondary-btn",
            **kwargs
        )
    
    def create_danger_button(self, text: str, **kwargs) -> gr.Button:
        """Создает кнопку для опасных действий"""
        return gr.Button(
            text,
            variant="stop",
            elem_classes="danger-btn",
            **kwargs
        )
    
    def create_chat_button(self) -> gr.Button:
        """Создает кнопку отправки сообщения"""
        return gr.Button(
            "Отправить",
            variant="primary",
            elem_classes="send-btn",
            scale=1
        )
    
    def create_new_chat_button(self) -> gr.Button:
        """Создает кнопку нового чата"""
        return gr.Button(
            "➕ Новый чат",
            variant="primary",
            size="lg",
            elem_classes="new-chat-btn"
        )
    
    def create_switch_chat_button(self) -> gr.Button:
        """Создает кнопку переключения чата"""
        return gr.Button(
            "🔄 Переключиться",
            variant="secondary",
            elem_classes="switch-chat-btn"
        )

# Глобальный экземпляр
buttons = ButtonComponents()