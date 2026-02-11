"""
Загрузка моделей и токенизаторов
"""
import os
from typing import Tuple, Optional, Any
from mlx_lm import load


class ModelLoader:
    """Загрузчик моделей для MLX"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def load(self) -> Tuple[Optional[Any], Optional[Any]]:
        """Загружает модель и токенизатор"""
        try:
            # Определяем путь для загрузки
            local_path = self.config.get("local_path")
            model_name = self.config.get("name", "Qwen/Qwen3-30B-A3B-MLX-4bit")
            
            load_path = self._determine_load_path(local_path, model_name)
            
            # Загружаем модель
            model, tokenizer = load(load_path)
            
            # Если скачали из HF и указан локальный путь - сохраняем
            if load_path == model_name and local_path and not os.path.exists(local_path):
                self._save_locally(model, tokenizer, local_path)
            
            return model, tokenizer
            
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            return None, None
    
    def _determine_load_path(self, local_path: Optional[str], model_name: str) -> str:
        """Определяет путь для загрузки модели"""
        if local_path and os.path.exists(local_path):
            print(f"📂 Загрузка модели {model_name} из model_config.local_path")
            return local_path
        elif local_path:
            print(f"⚠️ Локальный путь не существует: {local_path}")
            return model_name
        else:
            return model_name
    
    def _save_locally(self, model, tokenizer, local_path: str) -> bool:
        """Сохраняет модель локально для последующего использования"""
        try:
            os.makedirs(local_path, exist_ok=True)
            
            # Сохраняем модель
            if hasattr(model, 'save_pretrained'):
                model.save_pretrained(local_path)
            
            # Сохраняем токенизатор
            if hasattr(tokenizer, 'save_pretrained'):
                tokenizer.save_pretrained(local_path)
            
            print(f"✅ Модель сохранена в: {local_path}")
            return True
            
        except Exception as e:
            print(f"⚠️ Не удалось сохранить модель локально: {e}")
            return False