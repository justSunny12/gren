# /services/config_service.py
import yaml
import os
from typing import Dict, Any, Optional
from models.config_models import FullConfig
from services.user_config_service import user_config_service

class ConfigService:
    """Сервис для работы с конфигурацией"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._default_config: Optional[FullConfig] = None
        self._merged_config: Optional[FullConfig] = None
        self._user_config_service = user_config_service
    
    def load_default_config(self) -> FullConfig:
        """Загружает стандартную конфигурацию из YAML файлов"""
        config_data = {}
        
        # Загружаем все YAML файлы
        yaml_files = [
            "app_config.yaml",
            "model_config.yaml", 
            "ui_config.yaml",
            "paths_config.yaml"
        ]
        
        for yaml_file in yaml_files:
            file_path = os.path.join(self.config_dir, yaml_file)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                    self._merge_dicts(config_data, file_config)
            else:
                print(f"⚠️ Конфиг файл не найден: {file_path}")
        
        # Создаем Pydantic модель
        self._default_config = FullConfig(**config_data)
        return self._default_config
    
    def get_default_config(self) -> FullConfig:
        """Получает стандартную конфигурацию"""
        if self._default_config is None:
            return self.load_default_config()
        return self._default_config
    
    def get_config(self) -> FullConfig:
        """Получает объединенную конфигурацию (дефолтная + пользовательская)"""
        if self._merged_config is not None:
            return self._merged_config
        
        # Загружаем стандартную конфигурацию
        default_config = self.get_default_config()
        
        # Объединяем с пользовательской
        self._merged_config = self._user_config_service.get_merged_config(default_config)
        return self._merged_config
    
    def update_user_setting(self, section: str, key: str, value: Any) -> bool:
        """Обновляет пользовательскую настройку"""
        success = self._user_config_service.update_user_setting(section, key, value)
        
        if success:
            # Сбрасываем кэш объединенной конфигурации
            self._merged_config = None
        
        return success
    
    def update_user_settings_batch(self, settings: Dict[str, Dict[str, Any]]) -> bool:
        """Обновляет несколько пользовательских настроек за один раз (тихо)"""
        try:
            # Получаем текущую конфигурацию
            user_config = self._user_config_service.get_user_config()
            
            # Обновляем все настройки
            for section, section_settings in settings.items():
                if section == "generation" and hasattr(user_config, section):
                    for key, value in section_settings.items():
                        if hasattr(user_config.generation, key):
                            setattr(user_config.generation, key, value)
            
            # Сохраняем все одним вызовом
            success = self._user_config_service.save_user_config(user_config)
            
            if success:
                # Сбрасываем кэш объединенной конфигурации
                self._merged_config = None
            
            return success
            
        except Exception:
            return False
    
    def get_user_settings(self) -> Dict[str, Any]:
        """Получает текущие пользовательские настройки"""
        user_config = self._user_config_service.get_user_config()
        return user_config.to_dict()
    
    def reset_user_settings(self) -> bool:
        """Сбрасывает пользовательские настройки"""
        success = self._user_config_service.reset_to_defaults()
        
        if success:
            self._merged_config = None
        
        return success
    
    def save_config(self, config: FullConfig, config_dir: str = None):
        """Сохраняет конфигурацию в YAML файлы (только для стандартных настроек)"""
        if config_dir is None:
            config_dir = self.config_dir
        
        # Конвертируем модель в словарь
        config_dict = config.dict()
        
        # Сохраняем в разные файлы (ТОЛЬКО стандартные настройки)
        yaml_structure = {
            "app_config.yaml": {
                "app": config_dict.get("app", {}),
                "server": config_dict.get("server", {}),
                "queue": config_dict.get("queue", {}),
                "dialogs": config_dict.get("dialogs", {})
            },
            "model_config.yaml": {
                "model": config_dict.get("model", {}),
                "generation": config_dict.get("generation", {}),
                "chat_naming": config_dict.get("chat_naming", {})
            },
            "ui_config.yaml": {
                "ui": config_dict.get("ui", {})
            },
            "paths_config.yaml": {
                "paths": config_dict.get("paths", {})
            }
        }
        
        for filename, data in yaml_structure.items():
            file_path = os.path.join(config_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    def _merge_dicts(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Рекурсивно мержит словари"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dicts(target[key], value)
            else:
                target[key] = value
    
    def reload(self) -> FullConfig:
        """Перезагружает конфигурацию"""
        self._default_config = None
        self._merged_config = None
        return self.get_config()
    
    def get_css_content(self) -> str:
        """Получает CSS контент"""
        from services.css_generator import css_generator
        return css_generator.load_existing_css()

# Глобальный экземпляр конфиг сервиса
config_service = ConfigService()