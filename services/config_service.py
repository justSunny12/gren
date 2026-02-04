# /services/config_service.py
import yaml
import os
from typing import Dict, Any, Optional
import copy

class ConfigService:
    """Сервис для работы с конфигурацией"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._merged_config: Optional[Dict[str, Any]] = None
    
    def load_default_config(self) -> Dict[str, Any]:
        """Загружает стандартную конфигурацию из YAML файлов"""
        config_data = {}
        
        # Загружаем все YAML файлы из config директории
        try:
            if not os.path.exists(self.config_dir):
                print(f"⚠️ Директория конфигов не найдена: {self.config_dir}")
                return config_data
            
            yaml_files = [
                "app_config.yaml",
                "model_config.yaml", 
                "user_config.yaml"
            ]
            
            for yaml_file in yaml_files:
                file_path = os.path.join(self.config_dir, yaml_file)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_config = yaml.safe_load(f)
                            if file_config:
                                self._merge_dicts(config_data, file_config)
                        # print(f"✅ Загружен конфиг: {yaml_file}")
                    except Exception as e:
                        print(f"⚠️ Ошибка загрузки {yaml_file}: {e}")
                else:
                    print(f"ℹ️ Файл не найден (можно игнорировать): {yaml_file}")
        
        except Exception as e:
            print(f"❌ Критическая ошибка загрузки конфигов: {e}")
        
        return config_data
    
    def get_default_config(self) -> Dict[str, Any]:
        """Получает стандартную конфигурацию"""
        return self.load_default_config()
    
    def get_config(self) -> Dict[str, Any]:
        """Получает объединенную конфигурацию"""
        if self._merged_config is not None:
            return self._merged_config
        
        # Загружаем стандартную конфигурацию
        default_config = self.get_default_config()
        
        # Объединяем с пользовательской через user_config_service
        try:
            from services.user_config_service import user_config_service
            user_config = user_config_service.get_user_config()
            
            if not user_config.to_dict():
                self._merged_config = default_config
                return default_config
            
            # Объединяем конфигурации
            merged_data = user_config.merge_with_defaults(default_config)
            self._merged_config = merged_data
            return self._merged_config
            
        except ImportError as e:
            print(f"⚠️ UserConfigService не доступен: {e}")
            self._merged_config = default_config
            return default_config
        except Exception as e:
            print(f"⚠️ Ошибка объединения конфигов: {e}")
            self._merged_config = default_config
            return default_config
    
    def _merge_dicts(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Рекурсивно объединяет словари"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Рекурсивно объединяем вложенные словари
                self._merge_dicts(target[key], value)
            else:
                # Иначе заменяем или добавляем значение
                target[key] = copy.deepcopy(value)
    
    def update_user_settings_batch(self, settings: Dict[str, Dict[str, Any]]) -> bool:
        """Обновляет несколько пользовательских настроек"""
        try:
            from services.user_config_service import user_config_service
            
            user_config = user_config_service.get_user_config()
            
            for section, section_settings in settings.items():
                if section == "generation" and hasattr(user_config, section):
                    for key, value in section_settings.items():
                        if hasattr(user_config.generation, key):
                            setattr(user_config.generation, key, value)
            
            success = user_config_service.save_user_config(user_config)
            
            if success:
                self._merged_config = None
            
            return success
            
        except Exception as e:
            print(f"⚠️ Ошибка обновления настроек: {e}")
            return False
    
    def get_user_settings(self) -> Dict[str, Any]:
        """Получает текущие пользовательские настройки"""
        try:
            from services.user_config_service import user_config_service
            user_config = user_config_service.get_user_config()
            return user_config.to_dict()
        except Exception:
            return {}
    
    def reset_user_settings(self) -> bool:
        """Сбрасывает пользовательские настройки"""
        try:
            from services.user_config_service import user_config_service
            success = user_config_service.reset_to_defaults()
            
            if success:
                self._merged_config = None
            
            return success
            
        except Exception:
            return False
    
    def reload(self) -> Dict[str, Any]:
        """Перезагружает конфигурацию"""
        self._merged_config = None
        return self.get_config()

# Глобальный экземпляр конфиг сервиса
config_service = ConfigService()