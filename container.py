# /container.py (полностью обновленный)
from typing import Dict, Any

class Container:
    def __init__(self):
        self._services: Dict[str, Any] = {}
        # Убрано: self._use_mlx = True
    
    def get(self, name: str) -> Any:
        """Получает сервис по имени"""
        if name not in self._services:
            if name == "config_service":
                from services.config_service import ConfigService
                self._services["config_service"] = ConfigService()
                self._services["config_service"].get_config()
            elif name == "model_service":
                # ВСЕГДА используем ModelService (ранее MLXModelService)
                from services.model.manager import ModelService
                service = ModelService()
                self._services["model_service"] = service
                print("✅ Используется ModelService (MLX бэкенд)")
            elif name == "dialog_service":
                from services.dialogs import DialogService
                config = self.get_config()
                service = DialogService(config)  # Создаем экземпляр с конфигом
                self._services["dialog_service"] = service
            elif name == "chat_service":
                from services.chat.manager import ChatManager
                self._services["chat_service"] = ChatManager()
            elif name == "ui_handlers":
                from handlers import ui_handlers
                self._services["ui_handlers"] = ui_handlers
            else:
                raise ValueError(f"Сервис не найден: {name}")
        
        return self._services[name]
    
    # Убрано: метод set_backend
    
    def get_config(self):
        """Быстрый доступ к конфигурации"""
        return self.get("config_service").get_config()
    
    def get_chat_service(self):
        """Быстрый доступ к сервису чата"""
        return self.get("chat_service")
    
    def get_dialog_service(self):
        """Быстрый доступ к сервису диалогов"""
        return self.get("dialog_service")
    
    def get_model_service(self):
        """Быстрый доступ к сервису модели"""
        return self.get("model_service")
    
    def get_ui_handlers(self):
        """Быстрый доступ к UI обработчикам"""
        return self.get("ui_handlers")
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Получает статистику модели, если доступна"""
        try:
            model_service = self.get_model_service()
            if hasattr(model_service, 'get_stats'):
                return model_service.get_stats()
            else:
                return {"status": "Статистика не поддерживается"}
        except Exception as e:
            return {"status": f"Ошибка получения статистики: {str(e)}"}

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