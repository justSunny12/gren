# ui/layouts/sidebar_layout.py
import gradio as gr
from container import container

def create_sidebar_layout():
    config = container.get_config()
    gen_config = config.get("generation", {})
    with gr.Column(scale=1, min_width=380, elem_id="sidebar_container"):
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
        with gr.Accordion("⚙️ Параметры генерации", open=True, elem_classes="params-accordion") as params_accordion:
            max_tokens = gr.Slider(
                minimum=gen_config.get("min_max_tokens", 64),
                maximum=gen_config.get("max_max_tokens", 2048),
                value=gen_config.get("default_max_tokens", 512),
                step=64,
                label="Макс. токенов"
            )
            temperature = gr.Slider(
                minimum=gen_config.get("min_temperature", 0.1),
                maximum=gen_config.get("max_temperature", 1.5),
                value=gen_config.get("default_temperature", 0.7),
                step=0.1,
                label="Температура"
            )
            with gr.Row():
                reset_settings_btn = gr.Button("🔄 Сбросить к стандартным", variant="secondary", size="sm")
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
        "max_tokens": max_tokens,
        "temperature": temperature,
        "reset_settings_btn": reset_settings_btn,
        "chat_input": chat_input,
        "js_trigger": js_trigger,
        "generation_js_trigger": generation_js_trigger,
        "params_accordion": params_accordion
    }