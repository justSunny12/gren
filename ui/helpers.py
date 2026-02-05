# ui/helpers.py
import gradio as gr
from container import container

def reset_user_settings():
    """Тихий сброс пользовательских настроек к стандартным"""
    try:
        config_service = container.get("config_service")
        success = config_service.reset_user_settings()

        if success:
            default_config = config_service.get_default_config()
            gen_config = default_config.get("generation", {})

            return (
                gen_config.get("default_max_tokens", 512),
                gen_config.get("default_temperature", 0.7),
                gen_config.get("default_enable_thinking", False)
            )
        else:
            return gr.update(), gr.update(), gr.update()
    except Exception:
        return gr.update(), gr.update(), gr.update()

def on_slider_change(max_tokens, temperature, enable_thinking):
    """Тихий обработчик изменения параметров"""
    try:
        config_service = container.get("config_service")
        config_service.update_user_settings_batch({
            "generation": {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "enable_thinking": enable_thinking
            }
        })
        return gr.update(), gr.update(), gr.update()
    except Exception:
        return gr.update(), gr.update(), gr.update()