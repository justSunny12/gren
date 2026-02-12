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
                        container=True,
                    )
                
                # Область ввода (с кнопками внутри)
                with gr.Column(elem_classes="input-plate"):
                    with gr.Row(elem_classes="input-row"):
                        with gr.Column(elem_classes="chat-input-wrapper"):
                            user_input = gr.Textbox(
                                placeholder="Введите сообщение...",
                                show_label=False,
                                elem_classes="chat-input",
                                max_lines=4,
                                scale=9
                            )
                            # Контейнер для кнопок отправки и остановки
                            # Обе кнопки видимы, но управляются через CSS
                            with gr.Row(elem_classes="generation-buttons-wrapper"):
                                 # Контейнер для будущих левых кнопок
                                    gr.HTML('<div class="left-buttons"></div>', visible=False)  # скрыт, пока нет кнопок
                                    # Контейнер для правых кнопок (отправка/стоп)
                                    with gr.Row(elem_classes="right-buttons"):
                                        submit_btn = gr.Button(elem_classes="send-btn", scale=1)
                                        stop_btn = gr.Button(elem_classes="stop-btn", scale=1, visible=True)
                                    
                                    return sidebar_components, chatbot, user_input, submit_btn, stop_btn