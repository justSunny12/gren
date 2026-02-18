# /services/config_service.py
import yaml
import os
from typing import Dict, Any, Optional
import copy
from services.user_config_service import user_config_service
from container import container

class ConfigService:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._merged_config: Optional[Dict[str, Any]] = None
    
    @property
    def logger(self):
        if not hasattr(self, '_logger') or self._logger is None:
            self._logger = container.get_logger()
        return self._logger
    
    def load_default_config(self) -> Dict[str, Any]:
        config_data = {}
        try:
            if not os.path.exists(self.config_dir):
                return config_data
            yaml_files = [
                "app_config.yaml",
                "model_config.yaml",
                "user_config.yaml",
                "context_config.yaml",
                "search_config.yaml"
            ]
            for yaml_file in yaml_files:
                file_path = os.path.join(self.config_dir, yaml_file)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_config = yaml.safe_load(f)
                            if file_config:
                                self._merge_dicts(config_data, file_config)
                    except Exception:
                        pass
        except Exception:
            pass
        return config_data
    
    def get_default_config(self) -> Dict[str, Any]:
        return self.load_default_config()
    
    def get_config(self) -> Dict[str, Any]:
        if self._merged_config is not None:
            return self._merged_config
        default_config = self.get_default_config()
        try:
            user_config = user_config_service.get_user_config()
            if not user_config.to_dict():
                self._merged_config = default_config
                return default_config
            merged_data = user_config.merge_with_defaults(default_config)
            self._merged_config = merged_data
            return self._merged_config
        except Exception:
            self._merged_config = default_config
            return default_config
    
    def _merge_dicts(self, target: Dict[str, Any], source: Dict[str, Any]):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dicts(target[key], value)
            else:
                target[key] = copy.deepcopy(value)
    
    def update_user_settings_batch(self, settings: Dict[str, Any]) -> bool:
        try:
            user_config = user_config_service.get_user_config()

            for key, value in settings.items():
                if key == "generation" and isinstance(value, dict):
                    for k, v in value.items():
                        if hasattr(user_config.generation, k):
                            setattr(user_config.generation, k, v)
                elif key == "search_enabled":
                    user_config.search_enabled = value
                # при необходимости добавляем другие секции

            success = user_config_service.save_user_config(user_config)
            if success:
                self._merged_config = None
                user_config_service.invalidate_cache()
            else:
                self.logger.error("❌ Ошибка сохранения конфига")
            return success
        except Exception as e:
            self.logger.error("Исключение в update_user_settings_batch")
            return False
    
    def reset_user_settings(self) -> bool:
        try:
            success = user_config_service.reset_to_defaults()
            if success:
                self._merged_config = None
                user_config_service.invalidate_cache()
            return success
        except Exception:
            return False

config_service = ConfigService()