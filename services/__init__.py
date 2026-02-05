# services/__init__.py
"""
Пакет services
"""

# Экспортируем основные сервисы
from .config_service import ConfigService, config_service
from .dialog_service import DialogService, dialog_service
from .model_service import ModelService  # Изменено: ModelService вместо MLXModelService
from .chat_service import ChatService, chat_service
from .user_config_service import UserConfigService, user_config_service

__all__ = [
    'ConfigService', 'config_service',
    'ModelService',  # Изменено
    'DialogService', 'dialog_service',
    'ChatService', 'chat_service',
    'UserConfigService', 'user_config_service',
]