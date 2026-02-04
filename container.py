# /container.py
from typing import Dict, Any

class Container:
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._use_mlx = True  # Флаг для использования MLX
    
    def get(self, name: str) -> Any:
        """Получает сервис по имени"""
        if name not in self._services:
            if name == "config_service":
                from services.config_service import ConfigService
                self._services["config_service"] = ConfigService()
                self._services["config_service"].get_config()
            elif name == "model_service":
                # Используем MLX сервис если флаг установлен
                if self._use_mlx:
                    try:
                        from services.mlx_model_service import MLXModelService
                        service = MLXModelService()
                        self._services["model_service"] = service
                        print("✅ Используется MLX бэкенд")
                    except ImportError as e:
                        print(f"⚠️ MLX не доступен, используем PyTorch: {e}")
                        from services.model_service import ModelService
                        service = ModelService()
                        self._services["model_service"] = service
                else:
                    from services.model_service import ModelService
                    service = ModelService()
                    self._services["model_service"] = service
            elif name == "dialog_service":
                from services.dialog_service import dialog_service
                self._services["dialog_service"] = dialog_service
            elif name == "chat_service":
                from services.chat_service import chat_service
                self._services["chat_service"] = chat_service
            elif name == "ui_handlers":
                from logic.ui_handlers import ui_handlers
                self._services["ui_handlers"] = ui_handlers
            else:
                raise ValueError(f"Сервис не найден: {name}")
        
        return self._services[name]
    
    def set_backend(self, use_mlx: bool):
        """Устанавливает бэкенд (MLX или PyTorch)"""
        self._use_mlx = use_mlx
        if "model_service" in self._services:
            del self._services["model_service"]  # Принудительная перезагрузка
    
    def get_config(self):
        """Быстрый доступ к конфигурации (теперь возвращает словарь)"""
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