# /services/model_service.py (уменьшим логирование)
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from threading import Lock
from typing import Tuple, Any

class ModelService:
    """Сервис для работы с ML моделью"""
    
    def __init__(self):
        self.config = None
        self.model = None
        self.tokenizer = None
        self.generate_lock = Lock()
        self._initialized = False
    
    def _load_config(self):
        """Ленивая загрузка конфига"""
        if self.config is None:
            from container import container
            self.config = container.get_config()
    
    def initialize(self) -> Tuple[Any, Any, Lock]:
        """Инициализирует модель и токенизатор (минимальное логирование)"""
        if self._initialized:
            return self.model, self.tokenizer, self.generate_lock
        
        self._load_config()
        model_config = self.config.model
        
        # Минимальное сообщение
        print("📦 Загрузка модели...", end="", flush=True)
        
        # Определяем dtype для тензоров
        dtype_map = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "auto": None
        }
        dtype = dtype_map.get(model_config.dtype.value, torch.bfloat16)
        
        # Загружаем токенизатор (без сообщений)
        self.tokenizer = AutoTokenizer.from_pretrained(model_config.name)
        
        # Загружаем модель (без дополнительных сообщений)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_config.name,
            device_map="auto",
            dtype=dtype,
            attn_implementation=model_config.attn_implementation,
            low_cpu_mem_usage=model_config.low_cpu_mem_usage
        )
        
        # Включаем режим оценки
        self.model.eval()
        
        # Оптимизация потоков для Apple Silicon
        torch.set_num_threads(torch.get_num_threads())
        torch.set_num_interop_threads(1)
        
        self._initialized = True
        print(" ✅ Модель инициализирована")  # Завершаем сообщение галочкой
        
        return self.model, self.tokenizer, self.generate_lock
    
    def get_generation_params(self, **overrides):
        """Получает параметры генерации с возможностью переопределения"""
        if not self._initialized:
            self.initialize()
        
        self._load_config()
        gen_config = self.config.generation
        
        params = {
            "max_new_tokens": overrides.get("max_tokens", gen_config.default_max_tokens),
            "temperature": overrides.get("temperature", gen_config.default_temperature),
            "top_p": gen_config.default_top_p,
            "repetition_penalty": gen_config.default_repetition_penalty,
            "do_sample": True,
        }
        
        # Добавляем pad_token_id, если токенизатор инициализирован
        if self.tokenizer:
            params["pad_token_id"] = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
        
        return params
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли модель"""
        return self._initialized
    
    def cleanup(self):
        """Очищает ресурсы модели"""
        if self.model:
            del self.model
            self.model = None
        
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        
        self._initialized = False
        print("🧹 Ресурсы модели очищены")