# ui/main.py
from .resource_loader import ResourceLoader
from .app_builder import create_app

def create_main_ui():
    """Создает основной UI интерфейс (точка входа)"""
    
    # Загружаем ресурсы
    resource_loader = ResourceLoader()
    css_content = resource_loader.load_css()
    js_content = resource_loader.load_js()
    
    # Создаем приложение с событиями
    demo = create_app()
    
    return demo, css_content, js_content