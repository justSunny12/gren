# /services/user_config_service.py
import os
import json
import yaml
from typing import Dict, Any, Optional
from models.user_config_models import UserConfig
from models.config_models import FullConfig

class UserConfigService:
    """Сервис для работы с пользовательскими настройками"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.user_config_path = os.path.join(config_dir, "user_config.yaml")
        self._user_config: Optional[UserConfig] = None
        self._merged_config: Optional[FullConfig] = None
    
    def load_user_config(self) -> Optional[UserConfig]:
        """Загружает пользовательскую конфигурацию"""
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
            
        except Exception as e:
            print(f"⚠️ Не удалось загрузить пользовательскую конфигурацию: {e}")
            print("   Используются стандартные настройки")
            # Создаем пустую конфигурацию при ошибке
            self._user_config = UserConfig()
            return None
    
    def save_user_config(self, user_config: UserConfig) -> bool:
        """Сохраняет пользовательскую конфигурацию"""
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
            
        except Exception as e:
            print(f"❌ Ошибка сохранения пользовательской конфигурации: {e}")
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
    
    def get_merged_config(self, default_config: FullConfig) -> FullConfig:
        """Получает объединенную конфигурацию (дефолтная + пользовательская)"""
        if self._merged_config is not None:
            return self._merged_config
        
        user_config = self.get_user_config()
        
        if not user_config.to_dict():
            # Если пользовательских настроек нет, возвращаем дефолтную
            self._merged_config = default_config
            return default_config
        
        try:
            # Объединяем конфигурации
            merged_data = user_config.merge_with_defaults(default_config)
            self._merged_config = FullConfig(**merged_data)
            return self._merged_config
            
        except Exception as e:
            print(f"⚠️ Ошибка объединения конфигураций: {e}")
            print("   Используются стандартные настройки")
            self._merged_config = default_config
            return default_config
    
    def reset_to_defaults(self) -> bool:
        """Сбрасывает пользовательские настройки к стандартным"""
        try:
            if os.path.exists(self.user_config_path):
                os.remove(self.user_config_path)
            
            self._user_config = UserConfig()
            self._merged_config = None
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сброса настроек: {e}")
            return False

# Глобальный экземпляр
user_config_service = UserConfigService()