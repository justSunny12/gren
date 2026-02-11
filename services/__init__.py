# services/__init__.py
"""
Пакет services
"""

# Экспортируем сервисы
from .config_service import ConfigService, config_service
from .model.manager import ModelService
from .user_config_service import UserConfigService, user_config_service
from .dialogs import DialogManager
from .chat.manager import ChatManager

# Глобальный экземпляр будет создаваться в container.py
__all__ = [
    'ConfigService',
    'ModelService',
    'DialogManager',
    'ChatManager',
    'UserConfigService',
]