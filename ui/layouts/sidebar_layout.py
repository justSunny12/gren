# ui/layouts/sidebar_layout.py
import gradio as gr
import os
import base64

def create_sidebar_layout():
    with gr.Column(scale=1, min_width=380, elem_id="sidebar_container"):
        logo_path = os.path.join(os.path.dirname(__file__), "../..", "static", "images", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_base64 = base64.b64encode(f.read()).decode()
            logo_html = f'<div class="sidebar-logo"><img src="data:image/png;base64,{logo_base64}" alt="Logo"></div>'
        else:
            logo_html = '<div class="sidebar-logo">Логотип не найден</div>'
        gr.HTML(logo_html)
        
        create_dialog_btn = gr.Button(
            "➕ Новый чат",
            variant="primary",
            size="lg",
            elem_classes="new-chat-btn"
        )

        gr.HTML("""
        <div class="chat-list-container">
            <div class="chat-list" id="chat_list">
                <div style="text-align: center; padding: 20px; color: #64748b;">
                    Загрузка чатов...
                </div>
            </div>
        </div>
        """)

        # 👇 Скрытое поле для хранения настроек (обновляется только при загрузке)
        settings_data = gr.JSON(
            value={},
            visible=False,
            elem_id="settings_data"
        )

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

        js_trigger = gr.HTML(visible=False)
        generation_js_trigger = gr.HTML(
            visible=False,
            elem_id="generation_js_trigger"
        )

    return {
        "create_dialog_btn": create_dialog_btn,
        "chat_input": chat_input,
        "settings_data": settings_data,   # ← вернули
        "js_trigger": js_trigger,
        "generation_js_trigger": generation_js_trigger
    }