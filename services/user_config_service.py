# /services/user_config_service.py
import os
import json
import yaml
from typing import Dict, Any, Optional
from models.user_config_models import UserConfig

class UserConfigService:
    """Сервис для работы с пользовательскими настройками (с валидацией)"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.user_config_path = os.path.join(config_dir, "user_config.yaml")
        self._user_config: Optional[UserConfig] = None
        self._merged_config: Optional[Dict[str, Any]] = None
    
    def load_user_config(self) -> Optional[UserConfig]:
        """Загружает пользовательскую конфигурацию (с валидацией)"""
        if not os.path.exists(self.user_config_path):
            return None
        
        try:
            with open(self.user_config_path, 'r', encoding='utf-8') as f:
                user_data = yaml.safe_load(f)
            
            if not user_data:
                return None
            
            # Валидируем через Pydantic
            user_config = UserConfig(**user_data)
            self._user_config = user_config
            return user_config
            
        except Exception:
            return None
    
    def save_user_config(self, user_config: UserConfig) -> bool:
        """Сохраняет пользовательскую конфигурацию (тихо)"""
        try:
            # Создаем директорию если не существует
            os.makedirs(self.config_dir, exist_ok=True)
            
            # Конвертируем в словарь
            data = user_config.to_dict()
            
            # Сохраняем только если есть данные
            if not data:
                # Если файл существует, удаляем его
                if os.path.exists(self.user_config_path):
                    os.remove(self.user_config_path)
                self._user_config = user_config
                return True
            
            # Сохраняем в YAML
            with open(self.user_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self._user_config = user_config
            return True
            
        except Exception:
            return False
    
    def update_user_setting(self, section: str, key: str, value: Any) -> bool:
        """Обновляет конкретную настройку пользователя"""
        # Загружаем текущую конфигурацию
        user_config = self.get_user_config()
        
        # Обновляем нужную настройку
        if section == "generation":
            if hasattr(user_config.generation, key):
                setattr(user_config.generation, key, value)
        
        # Сохраняем
        return self.save_user_config(user_config)
    
    def get_user_config(self) -> UserConfig:
        """Получает пользовательскую конфигурацию (загружает если нужно)"""
        if self._user_config is None:
            config = self.load_user_config()
            if config is None:
                self._user_config = UserConfig()
        return self._user_config
    
    def merge_with_defaults(self, user_config: UserConfig, default_config: Dict[str, Any]) -> Dict[str, Any]:
        """Объединяет пользовательские настройки со стандартными"""
        result = default_config.copy()
        
        # Объединяем настройки генерации
        if user_config.generation.max_tokens is not None:
            result.setdefault("generation", {})["default_max_tokens"] = user_config.generation.max_tokens
        
        if user_config.generation.temperature is not None:
            result.setdefault("generation", {})["default_temperature"] = user_config.generation.temperature
        
        if user_config.generation.enable_thinking is not None:
            result.setdefault("generation", {})["default_enable_thinking"] = user_config.generation.enable_thinking
        
        return result
    
    def reset_to_defaults(self) -> bool:
        """Сбрасывает пользовательские настройки к стандартным"""
        try:
            if os.path.exists(self.user_config_path):
                os.remove(self.user_config_path)
            
            self._user_config = UserConfig()
            self._merged_config = None
            
            return True
            
        except Exception:
            return False

# Глобальный экземпляр
user_config_service = UserConfigService()