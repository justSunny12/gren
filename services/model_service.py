# /services/model_service.py
import torch
import gc
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from threading import Lock
from typing import Tuple, Any, Dict, Optional

class ModelService:
    """Сервис для работы с ML моделью"""
    
    def __init__(self):
        self.config = None
        self.model = None
        self.tokenizer = None
        self.generator = None
        self.generate_lock = Lock()
        self._initialized = False
        self.device = self._get_device()
    
    def _get_device(self):
        """Определяет лучшее устройство"""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print("Device set to use mps")
            return "mps"
        else:
            return "cpu"
    
    def _load_config(self):
        """Ленивая загрузка конфига"""
        if self.config is None:
            from container import container
            self.config = container.get_config()
    
    def initialize(self) -> Tuple[Any, Any, Lock]:
        """Инициализирует модель и токенизатор"""
        if self._initialized:
            return self.model, self.tokenizer, self.generate_lock
        
        self._load_config()
        model_config = self.config.model
        
        print(f"📦 Загрузка модели с Pipeline (device: {self.device})...", end="", flush=True)
        
        try:
            # Определяем dtype
            dtype_map = {
                "float16": torch.float16,
                "bfloat16": torch.bfloat16,
                "auto": torch.float16 if self.device in ["cuda", "mps"] else torch.float32
            }
            dtype = dtype_map.get(model_config.dtype.value, torch.float16)
            
            # Загружаем токенизатор
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_config.name,
                padding_side="left",
                trust_remote_code=True
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Используем dtype вместо torch_dtype
            self.generator = pipeline(
                "text-generation",
                model=model_config.name,
                tokenizer=self.tokenizer,
                dtype=dtype,
                device=self.device,
                model_kwargs={
                    "attn_implementation": model_config.attn_implementation,
                    "low_cpu_mem_usage": model_config.low_cpu_mem_usage,
                    "trust_remote_code": True,
                }
            )
            
            self.model = self.generator.model
            self.model.eval()
            
            self._initialized = True
            print(f" ✅ Модель инициализирована на {self.device}")
            
            return self.model, self.tokenizer, self.generate_lock
            
        except Exception as e:
            print(f" ❌ Ошибка загрузки модели: {e}")
            return None, None, self.generate_lock
    
    def generate_response(self, messages: list, max_tokens: int = 512, 
                        temperature: float = 0.7, enable_thinking: bool = False) -> str:
        """
        Генерирует ответ для совместимости с новым интерфейсом
        """
        if not self._initialized:
            self.initialize()
        
        # Тихий режим для прогрева
        if hasattr(self, '_warming_up') and self._warming_up:
            enable_thinking = False  # Принудительно выключаем thinking для прогрева
        
        try:
            # Используем enable_thinking если токенизатор поддерживает
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=enable_thinking
            )
        except TypeError:
            # Fallback для старых версий
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        
        # Получаем параметры генерации
        params = self.get_generation_params(max_tokens=max_tokens, temperature=temperature)
        
        # Для MPS при прогрессе используем минимальные параметры
        if self.device == "mps" and hasattr(self, '_warming_up') and self._warming_up:
            params = {"max_new_tokens": max_tokens}
        
        # Генерируем через пайплайн
        response = self.generate_with_pipeline(text, **params)
        
        return response
    
    def generate_with_pipeline(self, prompt: str, **generation_params) -> str:
        """Генерирует текст с использованием Pipeline"""
        if not self._initialized:
            self.initialize()
        
        with self.generate_lock:
            try:
                # Используем пайплайн для генерации
                results = self.generator(
                    prompt,
                    **generation_params,
                    return_full_text=False
                )
                
                if isinstance(results, list) and len(results) > 0:
                    return results[0]['generated_text']
                return ""
                
            except Exception as e:
                print(f"⚠️ Ошибка в generate_with_pipeline: {e}")
                return ""
    
    def get_generation_params(self, **overrides) -> Dict[str, Any]:
        """Получает параметры генерации для Pipeline"""
        if not self._initialized:
            self.initialize()
        
        self._load_config()
        gen_config = self.config.generation
        
        # Базовые параметры (поддерживаются всеми устройствами)
        params = {
            "max_new_tokens": overrides.get("max_tokens", gen_config.default_max_tokens),
            "temperature": overrides.get("temperature", gen_config.default_temperature),
            "do_sample": True,
            "num_return_sequences": 1,
        }
        
        # Устройство-специфичные параметры
        if self.device == "cuda":
            params.update({
                "top_p": gen_config.default_top_p,
                "repetition_penalty": gen_config.default_repetition_penalty,
            })
        elif self.device == "cpu":
            params.update({
                "top_p": gen_config.default_top_p,
            })
        # Для MPS не добавляем продвинутые параметры
        
        # Добавляем токены если токенизатор инициализирован
        if self.tokenizer:
            params["pad_token_id"] = self.tokenizer.pad_token_id
            params["eos_token_id"] = self.tokenizer.eos_token_id
        
        return params
    
    def chat_with_pipeline(self, messages: list, **generation_params) -> str:
        """Генерирует ответ для чата с использованием Pipeline"""
        if not self._initialized:
            self.initialize()
        
        # Форматируем промпт с помощью токенизатора
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Генерируем с пайплайном
        response = self.generate_with_pipeline(text, **generation_params)
        return response
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли модель"""
        return self._initialized
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает базовую статистику"""
        return {
            'device': self.device,
            'model_initialized': self._initialized,
            'service_type': 'ModelService',
        }
    
    def cleanup(self):
        """
        Очищает только временные данные
        Модель остается в памяти
        """
        print("🧹 Очистка временных данных ModelService...")
        
        # Очищаем системный кэш (не модель!)
        if self.device == "cuda":
            torch.cuda.empty_cache()
        elif self.device == "mps":
            torch.mps.empty_cache()
        
        gc.collect()
        
        print("✅ Временные данные очищены (модель в памяти)")
    
    def force_cleanup(self):
        """
        ПОЛНАЯ очистка всех ресурсов
        Только при завершении приложения
        """
        print("🧹 ПОЛНАЯ очистка всех ресурсов ModelService...")
        
        if self.generator:
            try:
                # Для MPS аккуратно отключаем
                if self.device == "mps" and hasattr(self.generator.model, 'to'):
                    self.generator.model = self.generator.model.to('cpu')
                
                del self.generator
            except Exception as e:
                print(f"⚠️ Ошибка при удалении генератора: {e}")
            finally:
                self.generator = None
        
        if self.model:
            try:
                del self.model
            except Exception as e:
                print(f"⚠️ Ошибка при удалении модели: {e}")
            finally:
                self.model = None
        
        if self.tokenizer:
            try:
                del self.tokenizer
            except Exception as e:
                print(f"⚠️ Ошибка при удалении токенизатора: {e}")
            finally:
                self.tokenizer = None
        
        # Системная очистка
        if self.device == "cuda":
            torch.cuda.empty_cache()
        elif self.device == "mps":
            torch.mps.empty_cache()
        
        gc.collect()
        
        self._initialized = False
        print("✅ Все ресурсы ModelService выгружены из памяти")

# Глобальный экземпляр (для обратной совместимости, если где-то используется)
model_service = ModelService()