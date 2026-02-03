# /ui/components/chat_bubble.py
import gradio as gr
from container import container

class ChatBubbleComponents:
    """Фабрика компонентов чата"""
    
    def __init__(self):
        self.config = container.get_config().get("ui", {})
    
    def create_chatbot(self, **kwargs) -> gr.Chatbot:
        """Создает компонент чатбота"""
        return gr.Chatbot(
            label="",
            show_label=False,
            height=None,
            avatar_images=(None, "https://avatars.githubusercontent.com/u/1024"),
            elem_classes="chatbot",
            **kwargs
        )
    
    def create_chat_container(self, **kwargs) -> gr.Column:
        """Создает контейнер для окна чата"""
        return gr.Column(
            elem_classes="chat-window-container",
            **kwargs
        )
    
    def create_input_container(self, **kwargs) -> gr.Column:
        """Создает контейнер для поля ввода"""
        return gr.Column(
            elem_classes="input-plate",
            **kwargs
        )
    
    def create_input_row(self, **kwargs) -> gr.Row:
        """Создает строку для поля ввода и кнопки"""
        return gr.Row(
            elem_classes="input-row",
            **kwargs
        )
    
    def create_chat_input_wrapper(self, **kwargs) -> gr.Column:
        """Создает обертку для поля ввода"""
        return gr.Column(
            elem_classes="chat-input-wrapper",
            **kwargs
        )
    
    def create_button_wrapper(self, **kwargs) -> gr.Column:
        """Создает обертку для кнопки"""
        return gr.Column(
            elem_classes="send-btn-wrapper",
            **kwargs
        )

# Глобальный экземпляр
chat_bubbles = ChatBubbleComponents()