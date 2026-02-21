# ui/layouts/main_layout.py
import gradio as gr

def create_main_layout():
    """Создаёт главный layout приложения (без параметров в сайдбаре)."""
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
                        avatar_images=(None, None),
                        elem_classes="chatbot"
                    )

                # Область ввода
                with gr.Column(elem_classes="input-plate"):
                    with gr.Row(elem_classes="input-row"):
                        with gr.Column(elem_classes="chat-input-wrapper"):
                            user_input = gr.Textbox(
                                placeholder="Введите сообщение...",
                                show_label=False,
                                elem_classes="chat-input",
                                max_lines=20,
                                autofocus=True,
                                scale=9
                            )
                            # Контейнер для кнопок
                            with gr.Row(elem_classes="generation-buttons-wrapper"):
                                # ЛЕВАЯ ГРУППА
                                with gr.Row(elem_classes="left-buttons"):
                                    thinking_btn = gr.Button(
                                        "Глубокое мышление",
                                        elem_classes="thinking-btn",
                                        scale=1
                                    )
                                    search_btn = gr.Button(
                                        "Поиск",
                                        elem_classes="search-btn",
                                        scale=1
                                    )
                                    settings_btn = gr.Button(
                                        elem_classes="settings-btn",
                                        scale=1
                                    )
                                # ПРАВАЯ ГРУППА
                                with gr.Row(elem_classes="right-buttons"):
                                    attach_btn = gr.Button(
                                        elem_classes="attach-btn",
                                        scale=1
                                    )
                                    submit_btn = gr.Button(
                                        elem_classes="send-btn",
                                        scale=1
                                    )
                                    stop_btn = gr.Button(
                                        elem_classes="stop-btn",
                                        scale=1,
                                        visible=True
                                    )

    # Возвращаем все созданные компоненты
    return (
        sidebar_components,
        chatbot,
        user_input,
        submit_btn,
        stop_btn,
        attach_btn,
        thinking_btn,
        search_btn,
        settings_btn
    )