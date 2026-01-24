# /ui/components/accordions.py
import gradio as gr
from ui.components.inputs import inputs

class AccordionComponents:
    """Фабрика аккордеонов"""
    
    def create_params_accordion(self) -> dict:
        """Создает аккордеон с параметрами модели"""
        with gr.Accordion("⚙️ Параметры", open=False, elem_classes="params-accordion"):
            sliders = inputs.create_params_sliders()
        
        return sliders

# Глобальный экземпляр
accordions = AccordionComponents()