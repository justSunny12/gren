# /container.py
from typing import Dict, Any

class Container:
    """Упрощенный контейнер зависимостей с поддержкой оптимизированной модели"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
    
    def get(self, name: str) -> Any:
        """Получает сервис по имени БЕЗ лишнего вывода"""
        if name not in self._services:
            # Ленивая загрузка сервисов
            if name == "config_service":
                from services.config_service import ConfigService
                self._services["config_service"] = ConfigService()
                # Загружаем пользовательскую конфигурацию при первом обращении
                self._services["config_service"].get_config()
            elif name == "model_service":
                from services.model_service import ModelService
                service = ModelService()
                self._services["model_service"] = service
            elif name == "dialog_service":
                from services.dialog_service import dialog_service
                self._services["dialog_service"] = dialog_service
            elif name == "chat_service":
                from services.chat_service import chat_service
                self._services["chat_service"] = chat_service
            elif name == "css_generator":
                from services.css_generator import css_generator
                self._services["css_generator"] = css_generator
            elif name == "ui_handlers":
                from logic.ui_handlers import ui_handlers
                self._services["ui_handlers"] = ui_handlers
            else:
                raise ValueError(f"Сервис не найден: {name}")
        
        return self._services[name]
    
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
    
    def get_css_generator(self):
        """Быстрый доступ к генератору CSS"""
        return self.get("css_generator")
    
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
    
    def reload_config(self):
        """Перезагружает конфигурацию всех сервисов"""
        if "config_service" in self._services:
            self._services["config_service"].reload()
        
        # Очищаем кэши зависимостей
        services_to_reload = ["chat_service", "css_generator", "ui_handlers"]
        for service_name in services_to_reload:
            if service_name in self._services:
                del self._services[service_name]
        
        print("✅ Конфигурация перезагружена")
    
    def reload_model(self):
        """Перезагружает модель"""
        if "model_service" in self._services:
            old_service = self._services["model_service"]
            
            # Очищаем ресурсы старой модели
            if hasattr(old_service, 'force_cleanup'):
                old_service.force_cleanup()
            
            # Удаляем старый сервис
            del self._services["model_service"]
            
            # Создаем новый
            from services.model_service import ModelService
            self._services["model_service"] = ModelService()
            print("✅ Модель перезагружена")
        
        # Также пересоздаем chat_service
        if "chat_service" in self._services:
            del self._services["chat_service"]
        
        print("✅ Модель и зависимые сервисы перезагружены")
    
    def cleanup_all(self):
        """Очищает все временные ресурсы (но оставляет модель в памяти)"""
        print("🧹 Очистка временных ресурсов контейнера...")
        
        services_count = len(self._services)
        cleaned_count = 0
        
        for name, service in list(self._services.items()):
            if name == "model_service":
                # Для модели только легкая очистка
                if hasattr(service, 'cleanup'):
                    service.cleanup()  # Не force_cleanup!
                    cleaned_count += 1
            else:
                # Для остальных сервисов обычная очистка
                if hasattr(service, 'cleanup'):
                    try:
                        service.cleanup()
                        cleaned_count += 1
                    except Exception as e:
                        print(f"⚠️ Ошибка очистки сервиса {name}: {e}")
        
        print(f"✅ Временные ресурсы {cleaned_count}/{services_count} сервисов очищены")
        print("💾 Модель остается в памяти для быстрой работы")
    
    def force_cleanup_all(self):
        """ПОЛНАЯ очистка ВСЕХ ресурсов (только при завершении приложения)"""
        print("🧹 ПОЛНАЯ очистка ВСЕХ ресурсов контейнера...")
        
        services_count = len(self._services)
        cleaned_count = 0
        
        # Сначала очищаем модель ПОЛНОСТЬЮ
        if "model_service" in self._services:
            print("🧠 Полная очистка модели...")
            service = self._services["model_service"]
            if hasattr(service, 'force_cleanup'):
                service.force_cleanup()
                cleaned_count += 1
        
        # Затем очищаем остальные сервисы
        for name, service in list(self._services.items()):
            if name != "model_service":  # Модель уже очистили
                if hasattr(service, 'cleanup'):
                    try:
                        service.cleanup()
                        cleaned_count += 1
                    except Exception as e:
                        print(f"⚠️ Ошибка очистки сервиса {name}: {e}")
        
        # Очищаем все ссылки
        self._services.clear()
        
        print(f"✅ Все {cleaned_count}/{services_count} сервисов полностью очищены")
        print("🧽 Память освобождена")
    
    def get_all_services(self) -> Dict[str, str]:
        """Возвращает список всех загруженных сервисов"""
        return {
            name: type(service).__name__
            for name, service in self._services.items()
        }

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