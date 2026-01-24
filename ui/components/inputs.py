# /ui/components/inputs.py
import gradio as gr
from container import container

class InputComponents:
    """Фабрика полей ввода с использованием конфигов"""
    
    def __init__(self):
        self.config = container.get_config().ui
    
    def create_chat_input(self, **kwargs) -> gr.Textbox:
        """Создает поле ввода для чата"""
        return gr.Textbox(
            placeholder="Введите сообщение...",
            lines=4,
            show_label=False,
            elem_classes="chat-input",
            max_lines=4,
            scale=9,
            **kwargs
        )
    
    def create_dropdown(self, choices: list = None, **kwargs) -> gr.Dropdown:
        """Создает выпадающий список"""
        return gr.Dropdown(
            choices=choices or [],
            interactive=True,
            scale=1,
            show_label=False,
            **kwargs
        )
    
    def create_slider(self, label: str, min_value: float, max_value: float, 
                     value: float, step: float = None, **kwargs) -> gr.Slider:
        """Создает слайдер"""
        return gr.Slider(
            minimum=min_value,
            maximum=max_value,
            value=value,
            step=step,
            label=label,
            **kwargs
        )
    
    def create_params_sliders(self) -> dict:
        """Создает слайдеры параметров модели"""
        gen_config = container.get_config().generation
        
        max_tokens = self.create_slider(
            label="Максимальное количество токенов",
            min_value=gen_config.min_max_tokens,
            max_value=gen_config.max_max_tokens,
            value=gen_config.default_max_tokens,
            step=64
        )
        
        temperature = self.create_slider(
            label="Температура",
            min_value=gen_config.min_temperature,
            max_value=gen_config.max_temperature,
            value=gen_config.default_temperature,
            step=0.1
        )
        
        enable_thinking = gr.Checkbox(  # ← ДОБАВЛЯЕМ
            label="🧠 Глубокое размышление",
            value=gen_config.default_enable_thinking,
            info="Включает внутренние размышления модели"
        )
        
        return {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "enable_thinking": enable_thinking  # ← ДОБАВЛЯЕМ В ВОЗВРАЩАЕМЫЙ СЛОВАРЬ
    }

# Глобальный экземпляр
inputs = InputComponents()