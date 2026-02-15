# services/context/summarizer_factory.py
"""
Фабрика для создания суммаризаторов с общей моделью.
"""
import threading
import time
import os
import asyncio
from typing import Dict, Any

import mlx.core as mx
from mlx_lm import load

from services.context.summarizers import L1Summarizer, L2Summarizer, BaseSummarizer


class SummarizerFactory:
    """Фабрика для создания суммаризаторов с ОДНОЙ общей моделью."""

    _instances: Dict[str, BaseSummarizer] = {}
    _shared_model = None
    _shared_tokenizer = None
    _shared_lock = None
    _preloaded = False
    _lock = threading.RLock()

    @classmethod
    def get_all_summarizers(cls, config: Dict[str, Any]) -> Dict[str, BaseSummarizer]:
        """Возвращает экземпляры L1 и L2 суммаризаторов, использующих ОДНУ модель."""
        with cls._lock:
            if "l1" in cls._instances and "l2" in cls._instances:
                return cls._instances.copy()

            model_config = config.get("model", {})
            if not model_config.get("local_path"):
                raise ValueError("В context_config.yaml отсутствует секция model.local_path")

            if cls._shared_model is None or cls._shared_tokenizer is None:
                cls._load_shared_model(model_config)

            cls._instances["l1"] = L1Summarizer(
                model_config, config,
                model=cls._shared_model,
                tokenizer=cls._shared_tokenizer,
                model_lock=cls._shared_lock
            )
            cls._instances["l2"] = L2Summarizer(
                model_config, config,
                model=cls._shared_model,
                tokenizer=cls._shared_tokenizer,
                model_lock=cls._shared_lock
            )

            return cls._instances.copy()

    @classmethod
    def _load_shared_model(cls, model_config: Dict[str, Any]):
        local_path = model_config.get("local_path")
        model_name = model_config.get("name", "Qwen/Qwen3-4B-MLX-4bit")

        if not local_path or not os.path.exists(local_path):
            raise FileNotFoundError(f"Модель суммаризации не найдена по пути: {local_path}")

        print(f"📂 Загрузка модели суммаризации {model_name}...")
        start = time.time()
        cls._shared_model, cls._shared_tokenizer = load(local_path)
        if cls._shared_tokenizer.pad_token is None:
            cls._shared_tokenizer.pad_token = cls._shared_tokenizer.eos_token
        cls._shared_tokenizer.padding_side = "left"
        cls._shared_lock = threading.RLock()
        print(f"   ✅ Модель загружена за {time.time() - start:.2f} сек")

    @classmethod
    def preload_summarizers(cls, config: Dict[str, Any]) -> bool:
        with cls._lock:
            if cls._preloaded:
                return True

            loading_config = config.get("loading", {})
            if not loading_config.get("preload", True):
                print("ℹ️ Предзагрузка суммаризаторов отключена в конфиге")
                return False

            try:
                cls.get_all_summarizers(config)

                if loading_config.get("warmup", True):
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    warmup_text = loading_config.get("warmup_text", "Тестовый текст для прогрева.")
                    loop.run_until_complete(cls._warmup(warmup_text))

                cls._preloaded = True
                return True
            except Exception as e:
                print(f"❌ Ошибка предзагрузки суммаризаторов: {e}")
                import traceback
                traceback.print_exc()
                return False

    @classmethod
    async def _warmup(cls, warmup_text: str):
        summarizers = cls.get_all_summarizers({})
        l1 = summarizers["l1"]
        try:
            await l1.summarize(warmup_text[:100], max_tokens=10, temperature=0.1)
            print("   ✅ Прогрев модели суммаризации завершён успешно")
        except Exception as e:
            print(f"⚠️ Ошибка прогрева: {e}")

    @classmethod
    def is_preloaded(cls) -> bool:
        return cls._preloaded

    @classmethod
    def unload_all(cls):
        with cls._lock:
            cls._instances.clear()
            if cls._shared_model is not None:
                cls._shared_model = None
                cls._shared_tokenizer = None
                cls._shared_lock = None
                if hasattr(mx, 'clear_cache'):
                    mx.clear_cache()
                print("✅ Единая модель суммаризации выгружена")
            cls._preloaded = False

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        with cls._lock:
            stats = {
                'shared_model_loaded': cls._shared_model is not None,
                'preloaded': cls._preloaded,
                'summarizers': {}
            }
            for name, summarizer in cls._instances.items():
                try:
                    stats['summarizers'][name] = summarizer.stats
                except Exception as e:
                    stats['summarizers'][name] = {'error': str(e)}
            return stats