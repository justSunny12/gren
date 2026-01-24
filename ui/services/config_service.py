# /services/config_service.py
import yaml
import os
from typing import Dict, Any, Optional
from models.config_models import FullConfig

class ConfigService:
    """Сервис для работы с конфигурацией"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._config: Optional[FullConfig] = None
    
    def load_config(self) -> FullConfig:
        """Загружает конфигурацию из YAML файлов"""
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
        self._config = FullConfig(**config_data)
        return self._config
    
    def get_config(self) -> FullConfig:
        """Получает конфигурацию (загружает если нужно)"""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def save_config(self, config: FullConfig, config_dir: str = None):
        """Сохраняет конфигурацию в YAML файлы"""
        if config_dir is None:
            config_dir = self.config_dir
        
        # Конвертируем модель в словарь
        config_dict = config.dict()
        
        # Сохраняем в разные файлы
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
        self._config = None
        return self.load_config()
    
    def get_css_content(self) -> str:
        """Получает CSS контент"""
        # Можно добавить кэширование здесь
        from services.css_generator import css_generator
        return css_generator.load_existing_css()

# Глобальный экземпляр конфиг сервиса
config_service = ConfigService()