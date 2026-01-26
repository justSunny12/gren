# /ui/layouts/main_layout.py
import gradio as gr

def create_main_layout():
    """Создает главный layout приложения"""
    with gr.Row(elem_classes="main-row"):
        # Сайдбар
        from ui.layouts.sidebar_layout import create_sidebar_layout
        sidebar_components = create_sidebar_layout()
        
        # Основное содержимое
        with gr.Column(elem_classes="main-content"):
            with gr.Column(elem_classes="chat-main-container"):
                # Окно чата
                with gr.Column(elem_classes="chat-window-container", elem_id="chat_window"):
                    chatbot = gr.Chatbot(
                        label="",
                        show_label=False,
                        height=None,
                        avatar_images=(None, "https://avatars.githubusercontent.com/u/1024"),
                        elem_classes="chatbot",
                        container=True,  # ← Ключевой параметр
                    )
                
                # Область ввода
                with gr.Column(elem_classes="input-plate"):
                    with gr.Row(elem_classes="input-row"):
                        with gr.Column(elem_classes="chat-input-wrapper"):
                            user_input = gr.Textbox(
                                placeholder="Введите сообщение...",
                                lines=4,
                                show_label=False,
                                elem_classes="chat-input",
                                max_lines=4,
                                scale=9
                            )
                        with gr.Column(elem_classes="send-btn-wrapper"):
                            submit_btn = gr.Button(
                                "Отправить", 
                                variant="primary", 
                                elem_classes="send-btn",
                                scale=1
                            )
    
    return sidebar_components, chatbot, user_input, submit_btn