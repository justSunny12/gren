# /container.py (убираем отладочные сообщения)
from typing import Dict, Any

class Container:
    """Упрощенный контейнер зависимостей"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initializing = False
    
    def get(self, name: str) -> Any:
        """Получает сервис по имени (без логирования)"""
        if name not in self._services:
            # Ленивая загрузка сервисов
            if name == "config_service":
                from services.config_service import ConfigService
                self._services["config_service"] = ConfigService()
            elif name == "model_service":
                from services.model_service import ModelService
                self._services["model_service"] = ModelService()
            elif name == "dialog_service":
                from services.dialog_service import dialog_service
                self._services["dialog_service"] = dialog_service
            elif name == "chat_service":
                from services.chat_service import ChatService
                self._services["chat_service"] = ChatService()
            else:
                raise ValueError(f"Сервис не найден: {name}")
        
        return self._services[name]
    
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