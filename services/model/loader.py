# services/model/loader.py
"""
Загрузка моделей и токенизаторов
"""
import os
from typing import Tuple, Optional, Any
from mlx_lm import load
from container import container


class ModelLoader:
    """Загрузчик моделей для MLX"""

    def __init__(self, config: dict):
        self.config = config
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    def load(self) -> Tuple[Optional[Any], Optional[Any]]:
        """Загружает модель и токенизатор"""
        try:
            local_path = self.config.get("local_path")
            model_name = self.config.get("name", "Qwen/Qwen3-30B-A3B-MLX-4bit")

            load_path = self._determine_load_path(local_path, model_name)

            # Логируем загрузку
            self.logger.info("📂 Загрузка модели %s из %s", model_name,
                            "model_config.local_path" if load_path == local_path else "Hugging Face")

            model, tokenizer = load(load_path)

            if load_path == model_name and local_path and not os.path.exists(local_path):
                self._save_locally(model, tokenizer, local_path)

            return model, tokenizer

        except Exception as e:
            self.logger.error("❌ Ошибка загрузки модели: %s", e)
            return None, None

    def _determine_load_path(self, local_path: Optional[str], model_name: str) -> str:
        """Определяет путь для загрузки модели"""
        if local_path and os.path.exists(local_path):
            return local_path
        elif local_path:
            self.logger.warning("⚠️ Локальный путь не существует: %s", local_path)
            return model_name
        else:
            return model_name

    def _save_locally(self, model, tokenizer, local_path: str) -> bool:
        """Сохраняет модель локально для последующего использования"""
        try:
            os.makedirs(local_path, exist_ok=True)

            if hasattr(model, 'save_pretrained'):
                model.save_pretrained(local_path)
            if hasattr(tokenizer, 'save_pretrained'):
                tokenizer.save_pretrained(local_path)

            self.logger.info("✅ Модель сохранена в: %s", local_path)
            return True

        except Exception as e:
            self.logger.warning("⚠️ Не удалось сохранить модель локально: %s", e)
            return False