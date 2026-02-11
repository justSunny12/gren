# ui/events/sidebar_events.py
import gradio as gr
from handlers import ui_handlers
from ui.helpers import on_slider_change, reset_user_settings

class SidebarEvents:
    """Обработчики событий сайдбара"""
    
    @staticmethod
    def bind_settings_events(max_tokens_slider, temperature_slider, enable_thinking_checkbox, 
                             reset_settings_btn):
        """Привязывает события настроек"""
        # Событие сброса настроек
        reset_settings_btn.click(
            fn=reset_user_settings,
            inputs=[],
            outputs=[max_tokens_slider, temperature_slider, enable_thinking_checkbox]
        )
        
        # События изменения слайдеров и чекбокса
        for param_control in [max_tokens_slider, temperature_slider, enable_thinking_checkbox]:
            param_control.change(
                fn=on_slider_change,
                inputs=[max_tokens_slider, temperature_slider, enable_thinking_checkbox],
                outputs=[max_tokens_slider, temperature_slider, enable_thinking_checkbox]
            )