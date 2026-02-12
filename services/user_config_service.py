# /services/user_config_service.py
import os
import yaml
from typing import Dict, Any, Optional
from models.user_config_models import UserConfig

class UserConfigService:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.user_config_path = os.path.join(config_dir, "user_config.yaml")
        self._user_config: Optional[UserConfig] = None
        self._merged_config: Optional[Dict[str, Any]] = None
    
    def load_user_config(self) -> Optional[UserConfig]:
        if not os.path.exists(self.user_config_path):
            return None
        try:
            with open(self.user_config_path, 'r', encoding='utf-8') as f:
                user_data = yaml.safe_load(f)
            if not user_data:
                return None
            return UserConfig(**user_data)
        except Exception:
            return None
    
    def save_user_config(self, user_config: UserConfig) -> bool:
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            data = user_config.to_dict()
            if not data:
                if os.path.exists(self.user_config_path):
                    os.remove(self.user_config_path)
                self._user_config = user_config
                return True
            with open(self.user_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
            self._user_config = user_config
            return True
        except Exception:
            return False
    
    def get_user_config(self, force_reload: bool = False) -> UserConfig:
        if force_reload:
            config = self.load_user_config()
            if config is None:
                self._user_config = UserConfig()
            else:
                self._user_config = config
        elif self._user_config is None:
            config = self.load_user_config()
            if config is None:
                self._user_config = UserConfig()
            else:
                self._user_config = config
        return self._user_config
    
    def invalidate_cache(self):
        self._user_config = None
        self._merged_config = None
    
    def reset_to_defaults(self) -> bool:
        try:
            if os.path.exists(self.user_config_path):
                os.remove(self.user_config_path)
            self._user_config = UserConfig()
            self._merged_config = None
            return True
        except Exception:
            return False

user_config_service = UserConfigService()