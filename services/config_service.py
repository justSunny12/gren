# /services/config_service.py
import yaml
import os
from typing import Dict, Any, Optional
import copy

class ConfigService:
    """Сервис для работы с конфигурацией (без валидации, читаем как есть)"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._merged_config: Optional[Dict[str, Any]] = None
    
    def load_default_config(self) -> Dict[str, Any]:
        """Загружает стандартную конфигурацию из YAML файлов (без валидации)"""
        config_data = {}
        
        # Загружаем все YAML файлы
        yaml_files = [
            "app_config.yaml",
            "model_config.yaml", 
            "ui_config.yaml"
        ]
        
        for yaml_file in yaml_files:
            file_path = os.path.join(self.config_dir, yaml_file)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                    self._merge_dicts(config_data, file_config or {})
        
        return config_data
    
    def get_default_config(self) -> Dict[str, Any]:
        """Получает стандартную конфигурацию"""
        return self.load_default_config()
    
    def get_config(self) -> Dict[str, Any]:
        """Получает объединенную конфигурацию (дефолтная + пользовательская)"""
        if self._merged_config is not None:
            return self._merged_config
        
        # Загружаем стандартную конфигурацию
        default_config = self.get_default_config()
        
        # Объединяем с пользовательской через user_config_service
        from services.user_config_service import user_config_service
        
        # Получаем пользовательские настройки
        user_config = user_config_service.get_user_config()
        
        if not user_config.to_dict():
            # Если пользовательских настроек нет, возвращаем дефолтную
            self._merged_config = default_config
            return default_config
        
        try:
            # Объединяем конфигурации
            merged_data = user_config.merge_with_defaults(default_config)
            self._merged_config = merged_data
            return self._merged_config
            
        except Exception:
            self._merged_config = default_config
            return default_config
    
    def update_user_settings_batch(self, settings: Dict[str, Dict[str, Any]]) -> bool:
        """Обновляет несколько пользовательских настроек за один раз (тихо)"""
        try:
            from services.user_config_service import user_config_service
            
            # Получаем текущую конфигурацию
            user_config = user_config_service.get_user_config()
            
            # Обновляем все настройки
            for section, section_settings in settings.items():
                if section == "generation" and hasattr(user_config, section):
                    for key, value in section_settings.items():
                        if hasattr(user_config.generation, key):
                            setattr(user_config.generation, key, value)
            
            # Сохраняем все одним вызовом
            success = user_config_service.save_user_config(user_config)
            
            if success:
                # Сбрасываем кэш объединенной конфигурации
                self._merged_config = None
            
            return success
            
        except Exception:
            return False
    
    def get_user_settings(self) -> Dict[str, Any]:
        """Получает текущие пользовательские настройки"""
        from services.user_config_service import user_config_service
        user_config = user_config_service.get_user_config()
        return user_config.to_dict()
    
    def reset_user_settings(self) -> bool:
        """Сбрасывает пользовательские настройки"""
        from services.user_config_service import user_config_service
        success = user_config_service.reset_to_defaults()
        
        if success:
            self._merged_config = None
        
        return success
    
    def _merge_dicts(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Рекурсивно мержит словари"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dicts(target[key], value)
            else:
                target[key] = value
    
    def reload(self) -> Dict[str, Any]:
        """Перезагружает конфигурацию"""
        self._merged_config = None
        return self.get_config()

# Глобальный экземпляр конфиг сервиса
config_service = ConfigService()