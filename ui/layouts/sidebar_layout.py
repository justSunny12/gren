# /ui/layouts/sidebar_layout.py
import gradio as gr

def create_sidebar_layout():
    """Создает layout боковой панели с новым списком чатов"""
    with gr.Column(scale=1, min_width=380, elem_id="sidebar_container"):
        # 1. Кнопка создания нового чата
        create_dialog_btn = gr.Button(
            "➕ Новый чат",
            variant="primary",
            size="lg",
            elem_classes="new-chat-btn"
        )
        
        # 2. Контейнер списка чатов
        gr.HTML("""
        <div class="chat-list-container">
            <div class="chat-list" id="chat_list">
                <div style="text-align: center; padding: 20px; color: #64748b;">
                    Загрузка чатов...
                </div>
            </div>
        </div>
        """)
        
        # 3. Параметры модели (аккордеон)
        with gr.Accordion("⚙️ Параметры генерации", open=True, elem_classes="params-accordion") as params_accordion:
            max_tokens = gr.Slider(
                minimum=64, maximum=2048, value=512, step=64,
                label="Макс. токенов"
            )
            temperature = gr.Slider(
                minimum=0.1, maximum=1.5, value=0.7, step=0.1,
                label="Температура"
            )
            enable_thinking = gr.Checkbox(
                label="🧠 Глубокое размышление",
                value=False,
                info="Включает внутренние размышления модели"
            )
            
            # Кнопка сброса настроек
            with gr.Row():
                reset_settings_btn = gr.Button("🔄 Сбросить к стандартным", variant="secondary", size="sm")
        
        # Скрытое поле для передачи ID выбранного чата
        chat_input = gr.Textbox(
            elem_id="chat_input_field",
            label="",
            show_label=False,
            container=False,
            scale=0,
            min_width=50,
            elem_classes="hidden-input",
            interactive=True
        )
        
        # Скрытый триггер для JavaScript
        js_trigger = gr.HTML(visible=False)
        
        # Статус
        status_text = gr.Markdown("✅ Готов к работе", elem_classes="status-bar")
    
    return {
        "create_dialog_btn": create_dialog_btn,
        "status_text": status_text,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "enable_thinking": enable_thinking,
        "reset_settings_btn": reset_settings_btn,
        "chat_input": chat_input,
        "js_trigger": js_trigger,
        "params_accordion": params_accordion
    }