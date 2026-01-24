# /ui/layouts/chat_layout.py
import gradio as gr

def create_chat_layout():
    """Создает layout чата и возвращает компоненты"""
    chatbot = gr.Chatbot(
        label="",
        show_label=False,
        height=None,
        avatar_images=(None, "https://avatars.githubusercontent.com/u/1024"),
        elem_classes="chatbot"
    )
    
    with gr.Column(elem_classes="chat-main-container"):
        # Окно чата
        with gr.Column(elem_classes="chat-window-container"):
            pass  # Chatbot уже создан выше
        
        # Общая плашка для ввода и кнопки
        with gr.Column(elem_classes="input-plate"):
            with gr.Row(elem_classes="input-row"):
                # Контейнер для поля ввода
                with gr.Column(elem_classes="chat-input-wrapper"):
                    user_input = gr.Textbox(
                        placeholder="Введите сообщение...",
                        lines=4,
                        show_label=False,
                        elem_classes="chat-input",
                        max_lines=4,
                        scale=9
                    )
                # Контейнер для кнопки
                with gr.Column(elem_classes="send-btn-wrapper"):
                    submit_btn = gr.Button(
                        "Отправить", 
                        variant="primary", 
                        elem_classes="send-btn",
                        scale=1
                    )
    
    return chatbot, user_input, submit_btn