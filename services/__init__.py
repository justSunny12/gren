# services/__init__.py
"""
Пакет services
"""

# Экспортируем сервисы
from .config_service import ConfigService, config_service
from .model_service import ModelService
from .user_config_service import UserConfigService, user_config_service
from .dialogs import DialogService

# Глобальный экземпляр будет создаваться в container.py
__all__ = [
    'ConfigService', 'config_service',
    'ModelService',
    'DialogService',
    'ChatManager',
    'UserConfigService', 'user_config_service',
]