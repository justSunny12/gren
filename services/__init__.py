# /services/__init__.py
"""
Пакет services
"""

# Экспортируем основные сервисы для удобного импорта
from .config_service import ConfigService, config_service
from .dialog_service import DialogService, dialog_service
from .model_service import ModelService
from .chat_service import ChatService, chat_service
from .css_generator import CSSGenerator, css_generator

__all__ = [
    'ConfigService', 'config_service',
    'ModelService',
    'DialogService', 'dialog_service',
    'ChatService', 'chat_service',
    'CSSGenerator', 'css_generator'
]