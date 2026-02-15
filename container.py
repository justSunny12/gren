# container.py (обновленная версия)
from typing import Dict, Any, Callable, Optional

class Container:
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._setup_default_factories()
    
    def _setup_default_factories(self):
        """Регистрация фабрик по умолчанию"""
        self._factories.update({
            "config_service": self._create_config_service,
            "model_service": self._create_model_service,
            "dialog_service": self._create_dialog_service,
            "chat_service": self._create_chat_service,
            "ui_mediator": self._create_ui_mediator,
        })
    
    def _create_config_service(self):
        from services.config_service import ConfigService
        service = ConfigService()
        service.get_config()  # Инициализация
        return service
    
    def _create_model_service(self):
        from services.model.manager import ModelService
        return ModelService()
    
    def _create_dialog_service(self):
        from services.dialogs import DialogService
        config = self.get_config()
        return DialogService(config)
    
    def _create_chat_service(self):
        from services.chat.manager import ChatManager
        return ChatManager()
    
    def _create_ui_mediator(self):
        from handlers.mediator import UIMediator
        return UIMediator()
    
    def register(self, name: str, factory: Callable):
        """Регистрация фабрики для создания сервиса"""
        self._factories[name] = factory
    
    def get(self, name: str) -> Any:
        """Получает сервис по имени (ленивое создание)"""
        if name not in self._services:
            if name in self._factories:
                self._services[name] = self._factories[name]()
            else:
                raise ValueError(f"Фабрика не найдена для сервиса: {name}")
        
        return self._services[name]
    
    # Быстрые методы доступа для обратной совместимости
    def get_config(self):
        return self.get("config_service").get_config()
    
    def get_chat_service(self):
        return self.get("chat_service")
    
    def get_dialog_service(self):
        return self.get("dialog_service")
    
    def get_model_service(self):
        return self.get("model_service")

# Глобальный контейнер
container = Container()

# Вспомогательные функции для обратной совместимости
def get_config():
    return container.get_config()

def get_chat_service():
    return container.get_chat_service()

def get_dialog_service():
    return container.get_dialog_service()

def get_model_service():
    return container.get_model_service()