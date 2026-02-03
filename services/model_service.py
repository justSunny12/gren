# /services/model_service.py
import torch
import gc
import time
import platform
from typing import Dict, Any, List, Optional
from threading import Lock
from datetime import datetime
from transformers import pipeline, AutoTokenizer
import psutil

class ModelService:
    """
    Оптимизированный сервис для работы с моделями
    Модель загружается один раз и остается в памяти
    """
    
    def __init__(self):
        self.config = None
        self.generator = None
        self.tokenizer = None
        self.generate_lock = Lock()
        self._initialized = False
        self._warming_up = False
        
        # Определяем устройство
        self.device = self._get_device()
        
        # Мониторинг производительности
        self.generation_stats = {
            'total_requests': 0,
            'batch_requests': 0,
            'avg_generation_time': 0,
            'total_tokens_generated': 0,
            'last_cleanup': datetime.now()
        }
        
        # Кэш параметров генерации - НИКОГДА не очищаем между запросами!
        self.param_cache = {}
        
        # Временные буферы (можно очищать)
        self.temp_buffers = []
        self.temp_tensors = []
        
        # Batch очередь
        self.batch_size = 1
    
    def _get_device(self):
        """Определяет лучшее устройство для запуска"""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print("Device set to use mps")
            return "mps"
        else:
            return "cpu"
    
    def _get_dtype(self):
        """Определяет оптимальный dtype для устройства"""
        if self.device == "cuda":
            return torch.float16
        elif self.device == "mps":
            return torch.float16
        else:
            return torch.float32
    
    def initialize(self, force_reload: bool = False):
        """
        Инициализирует модель один раз при первом вызове
        Возвращает кортеж для совместимости
        """
        if self._initialized and not force_reload:
            return self.generator.model if self.generator else None, self.tokenizer, self.generate_lock
        
        # Загрузка конфигурации
        from container import container
        self.config = container.get_config()
        model_config = self.config.model
        
        start_time = time.time()
        
        try:
            # Используем оптимальный dtype для устройства
            dtype = self._get_dtype()
            
            print(f"📦 Загрузка модели {model_config.name}...")
            print(f"   device: {self.device}")
            print(f"   dtype: {dtype}")
            
            # Оптимизации для разных устройств
            if self.device == "cuda":
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.benchmark = True
            elif self.device == "mps":
                torch.mps.empty_cache()
            
            # Загружаем токенизатор
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_config.name,
                trust_remote_code=True
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.padding_side = "left"
            
            # Подготавливаем параметры для pipeline
            model_kwargs = {
                "attn_implementation": model_config.attn_implementation,
                "low_cpu_mem_usage": model_config.low_cpu_mem_usage,
            }
            
            if self.device == "cuda":
                model_kwargs["device_map"] = "auto"
            
            # Загружаем модель один раз
            self.generator = pipeline(
                "text-generation",
                model=model_config.name,
                tokenizer=self.tokenizer,
                device=self.device if self.device != "mps" else -1,
                batch_size=self.batch_size,
                model_kwargs=model_kwargs
            )
            
            self._initialized = True
            
            load_time = time.time() - start_time
                        
            return self.generator.model, self.tokenizer, self.generate_lock
            
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            return None, None, self.generate_lock
    
    def get_generation_params(self, max_tokens: Optional[int] = None, 
                             temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        Получает параметры генерации
        """
        if not self._initialized:
            self.initialize()
        
        if max_tokens is None:
            max_tokens = self.config.generation.default_max_tokens
        if temperature is None:
            temperature = self.config.generation.default_temperature
        
        # Базовые параметры
        params = {
            "max_new_tokens": max_tokens,
            "temperature": max(temperature, 0.01),
            "do_sample": temperature > 0.1,
        }
        
        # Устройство-специфичные параметры
        if self.device == "cuda":
            params.update({
                "top_p": self.config.generation.default_top_p,
                "repetition_penalty": self.config.generation.default_repetition_penalty,
            })
        elif self.device == "cpu":
            params.update({
                "top_p": self.config.generation.default_top_p,
            })
        # MPS оставляем с базовыми параметрами
        
        if self.tokenizer:
            params["pad_token_id"] = self.tokenizer.pad_token_id
            params["eos_token_id"] = self.tokenizer.eos_token_id
        
        return params
    
    def generate_response(self, messages: list, max_tokens: int = 512, 
                        temperature: float = 0.7, enable_thinking: bool = False) -> str:
        """
        Генерирует ответ с использованием enable_thinking параметра токенизатора Qwen
        """
        if not self._initialized:
            self.initialize()
        
        self.generation_stats['total_requests'] += 1
        
        # Выключаем Thinking для прогрева
        if hasattr(self, '_warming_up') and self._warming_up:
            # Тихий режим для прогрева
            enable_thinking = False  # Принудительно выключаем thinking для прогрева
        
        try:
            # Используем встроенный параметр enable_thinking токенизатора Qwen
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=enable_thinking  # ← Штатный параметр модели
            )
        except TypeError as e:
            # Если токенизатор не поддерживает enable_thinking (старая версия)
            if not (hasattr(self, '_warming_up') and self._warming_up):
                print(f"⚠️ Токенизатор не поддерживает enable_thinking: {e}")
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        
        # Получаем параметры генерации
        params = self.get_generation_params(max_tokens, temperature)
        
        start_time = time.time()
        
        with self.generate_lock:
            try:
                # Базовые параметры
                gen_params = {
                    "max_new_tokens": params["max_new_tokens"],
                    "temperature": params.get("temperature", 0.7),
                    "do_sample": params.get("do_sample", True),
                    "return_full_text": False,
                }
                
                # Для MPS убираем параметры которые могут вызывать предупреждения
                if self.device == "cuda":
                    gen_params.update({
                        "top_p": params.get("top_p", 0.9),
                        "repetition_penalty": params.get("repetition_penalty", 1.1),
                    })
                elif self.device == "mps":
                    # MPS имеет ограниченную поддержку параметров
                    # Убираем параметры вызывающие предупреждения при прогреве
                    if hasattr(self, '_warming_up') and self._warming_up:
                        gen_params = {
                            "max_new_tokens": params["max_new_tokens"],
                            "return_full_text": False,
                        }
                
                # Генерируем
                results = self.generator(prompt, **gen_params)
                
                if results and len(results) > 0:
                    response = results[0]['generated_text'].strip()
                    response_tokens = len(self.tokenizer.encode(response))
                    self.generation_stats['total_tokens_generated'] += response_tokens
                else:
                    response = ""
                    
            except Exception as e:
                if not (hasattr(self, '_warming_up') and self._warming_up):
                    print(f"❌ Ошибка генерации: {e}")
                response = "Извините, произошла ошибка при генерации ответа."
        
        generation_time = time.time() - start_time
        
        # Обновляем статистику
        if self.generation_stats['total_requests'] > 1:
            old_avg = self.generation_stats['avg_generation_time']
            new_count = self.generation_stats['total_requests']
            self.generation_stats['avg_generation_time'] = (
                old_avg * (new_count - 1) + generation_time
            ) / new_count
        
        return response
    
    def _print_memory_info(self):
        """Выводит информацию об использовании памяти"""
        try:
            # Не выводим если в режиме прогрева
            if hasattr(self, '_warming_up') and self._warming_up:
                return
                
            if self.device == "cuda":
                gpu_memory = torch.cuda.memory_allocated() / 1024**3
                gpu_memory_max = torch.cuda.max_memory_allocated() / 1024**3
                print(f"💾 GPU память: {gpu_memory:.2f} GB (пик: {gpu_memory_max:.2f} GB)")
            elif self.device == "mps":
                print(f"💾 MPS устройство: доступно")
            
            process = psutil.Process()
            memory_info = process.memory_info()
            ram_usage = memory_info.rss / 1024**3
            print(f"💾 RAM использование: {ram_usage:.2f} GB")
            
        except Exception as e:
            # Не выводим ошибку если в режиме прогрева
            if not (hasattr(self, '_warming_up') and self._warming_up):
                print(f"⚠️ Не удалось получить информацию о памяти: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику генерации
        """
        if self.generation_stats['total_requests'] > 0:
            tokens_per_request = (
                self.generation_stats['total_tokens_generated'] / 
                self.generation_stats['total_requests']
                if self.generation_stats['total_requests'] > 0 else 0
            )
        else:
            tokens_per_request = 0
        
        return {
            'device': self.device,
            'total_requests': self.generation_stats['total_requests'],
            'batch_requests': self.generation_stats['batch_requests'],
            'avg_generation_time_ms': self.generation_stats['avg_generation_time'] * 1000,
            'total_tokens_generated': self.generation_stats['total_tokens_generated'],
            'tokens_per_request': tokens_per_request,
            'param_cache_size': len(self.param_cache),
            'model_initialized': self._initialized,
        }
    
    def cleanup(self):
        """
        Очищает только временные данные
        Модель и кэш параметров остаются в памяти
        """
        print("🧹 Очистка временных данных...")
        
        # Очищаем только временные буферы
        self.temp_buffers.clear()
        
        # Освобождаем временные тензоры
        for tensor in self.temp_tensors:
            try:
                if hasattr(tensor, 'detach'):
                    tensor.detach()
                if hasattr(tensor, 'cpu'):
                    tensor.cpu()
            except:
                pass
        self.temp_tensors.clear()
        
        # Очищаем системный кэш (не модель!)
        if self.device == "cuda":
            torch.cuda.empty_cache()
        elif self.device == "mps":
            torch.mps.empty_cache()
        
        gc.collect()
        
        self.generation_stats['last_cleanup'] = datetime.now()
        print("✅ Временные данные очищены (модель и кэш в памяти)")
    
    def force_cleanup(self):
        """
        ПОЛНАЯ очистка всех ресурсов
        ТОЛЬКО при завершении приложения
        """
        print("🧹 ПОЛНАЯ очистка ВСЕХ ресурсов модели...")
        
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
        
        if self.tokenizer:
            try:
                del self.tokenizer
            except:
                pass
            self.tokenizer = None
        
        # Очищаем ВСЕ кэши (только при завершении!)
        self.param_cache.clear()
        self.temp_buffers.clear()
        self.temp_tensors.clear()
        
        # Системная очистка
        if self.device == "cuda":
            torch.cuda.empty_cache()
        elif self.device == "mps":
            torch.mps.empty_cache()
        
        gc.collect()
        
        self._initialized = False
        print("✅ Все ресурсы модели выгружены из памяти")
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли модель"""
        return self._initialized