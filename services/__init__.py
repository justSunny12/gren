"""
Пакет services
"""

# Экспортируем сервисы (обновленная версия)
from .config_service import ConfigService, config_service
from .model_service import ModelService
from .chat_service import ChatService, chat_service
from .user_config_service import UserConfigService, user_config_service
from .dialogs import DialogService  # Экспортируем класс

# Глобальный экземпляр будет создаваться в container.py
__all__ = [
    'ConfigService', 'config_service',
    'ModelService',
    'DialogService',  # ✅ Добавлено
    'ChatService', 'chat_service',
    'UserConfigService', 'user_config_service',
]