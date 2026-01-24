# /ui/layouts/sidebar_layout.py
import gradio as gr

def create_sidebar_layout():
    """Создает layout боковой панели"""
    with gr.Column(scale=1, min_width=300, elem_id="sidebar_container"):
        # Выбор чата
        dialog_dropdown = gr.Dropdown(
            choices=[],
            interactive=True,
            scale=1,
            show_label=False
        )
        
        with gr.Row():
            switch_dialog_btn = gr.Button("🔄 Переключиться", variant="secondary")
        
        # Разделитель
        gr.HTML("<hr class='sidebar-divider'>")
        
        with gr.Row():
            delete_dialog_btn = gr.Button("🗑️ Удалить", variant="stop", min_width=140)
        
        # Разделитель
        gr.HTML("<hr class='sidebar-divider'>")
        
        # Кнопка создания нового чата
        create_dialog_btn = gr.Button("➕ Новый чат", variant="primary", size="lg")
        
        # Разделитель
        gr.HTML("<hr class='sidebar-divider'>")
        
        # Параметры модели
        with gr.Accordion("⚙️ Параметры", open=False, elem_classes="params-accordion"):
            max_tokens = gr.Slider(
                minimum=64, maximum=2048, value=512, step=64,
                label="Максимальное количество токенов"
            )
            temperature = gr.Slider(
                minimum=0.1, maximum=1.5, value=0.7, step=0.1,
                label="Температура"
            )
            enable_thinking = gr.Checkbox(  # ← ДОБАВЛЯЕМ
                label="🧠 Глубокое размышление",
                value=False,
                info="Включает внутренние размышления модели"
            )
        
        # Статус
        status_text = gr.Markdown("✅ Готов к работе")
    
    return {
        "create_dialog_btn": create_dialog_btn,
        "dialog_dropdown": dialog_dropdown,
        "switch_dialog_btn": switch_dialog_btn,
        "delete_dialog_btn": delete_dialog_btn,
        "status_text": status_text,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "enable_thinking": enable_thinking  # ← ДОБАВЛЯЕМ В ВОЗВРАЩАЕМЫЙ СЛОВАРЬ
    }