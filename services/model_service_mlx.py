# /services/model_service_mlx.py
import mlx.core as mx
import mlx.nn as nn
from mlx_lm import load, generate
import time
import platform
from typing import Dict, Any, List
from threading import Lock
from datetime import datetime
import json

class ModelServiceMLX:
    """Оптимизированный сервис для работы с моделями через MLX"""
    
    def __init__(self):
        self.config = None
        self.model = None
        self.tokenizer = None
        self.generate_lock = Lock()
        self._initialized = False
        self._warming_up = False
        
        # Мониторинг производительности
        self.generation_stats = {
            'total_requests': 0,
            'avg_generation_time': 0,
            'total_tokens_generated': 0,
            'last_cleanup': datetime.now()
        }
        
    def initialize(self, force_reload: bool = False):
        """
        Инициализирует модель через MLX
        """
        if self._initialized and not force_reload:
            return self.model, self.tokenizer, self.generate_lock
        
        # Загрузка конфигурации
        from container import container
        self.config = container.get_config()
        model_config = self.config.get("model", {})
        
        start_time = time.time()
        
        try:
            print(f"📦 Загрузка модели {model_config.get('name', 'Qwen/Qwen3-4B')} через MLX...")
            print(f"   device: MLX (Apple Silicon)")
            
            # Загружаем модель через mlx-lm
            model_name = model_config.get("name", "Qwen/Qwen3-4B")
            
            print("   ⏳ Загрузка модели... (это может занять некоторое время)")
            
            self.model, self.tokenizer = load(model_name)
            
            self._initialized = True
            
            load_time = time.time() - start_time
            print(f"✅ Модель загружена за {load_time:.2f} секунд")
            
            # Прогрев модели
            print("🔥 Прогрев модели...")
            try:
                self._warming_up = True
                warmup_prompt = [{"role": "user", "content": "Привет"}]
                warmup_response = self.generate_response(
                    warmup_prompt, 
                    max_tokens=10,
                    temperature=0.1
                )
                self._warming_up = False
                print("✅ Модель прогрета успешно")
            except Exception as e:
                print(f"ℹ️ Прогрев не удался: {e}, но модель загружена")
            
            return self.model, self.tokenizer, self.generate_lock
            
        except Exception as e:
            print(f"❌ Ошибка загрузки модели через MLX: {e}")
            import traceback
            traceback.print_exc()
            return None, None, self.generate_lock
    
    def get_generation_params(self, max_tokens: int = None, 
                             temperature: float = None) -> Dict[str, Any]:
        """
        Получает параметры генерации для MLX
        """
        if not self._initialized:
            self.initialize()
        
        if max_tokens is None:
            max_tokens = self.config.get("generation", {}).get("default_max_tokens", 512)
        if temperature is None:
            temperature = self.config.get("generation", {}).get("default_temperature", 0.7)
        
        # Базовые параметры для MLX
        params = {
            "max_tokens": max_tokens,
            "temp": max(temperature, 0.01),
            "top_p": self.config.get("generation", {}).get("default_top_p", 0.9),
        }
        
        return params
    
    def generate_response(self, messages: list, max_tokens: int = 512, 
                        temperature: float = 0.7, enable_thinking: bool = False) -> str:
        """
        Генерирует ответ через MLX
        """
        if not self._initialized:
            self.initialize()
        
        self.generation_stats['total_requests'] += 1
        
        # Выключаем Thinking для прогрева
        if self._warming_up:
            enable_thinking = False
        
        try:
            # Форматируем промпт для токенизатора
            if hasattr(self.tokenizer, 'apply_chat_template'):
                try:
                    # Пытаемся использовать enable_thinking если токенизатор поддерживает
                    prompt = self.tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True,
                        enable_thinking=enable_thinking
                    )
                except TypeError:
                    # Если не поддерживает enable_thinking
                    prompt = self.tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True
                    )
            else:
                # Fallback для простого токенизатора
                prompt = ""
                for msg in messages:
                    if msg["role"] == "user":
                        prompt += f"Пользователь: {msg['content']}\n"
                    elif msg["role"] == "assistant":
                        prompt += f"Ассистент: {msg['content']}\n"
                prompt += "Ассистент: "
        
        except Exception as e:
            if not self._warming_up:
                print(f"⚠️ Ошибка форматирования промпта: {e}")
            prompt = messages[-1]["content"] if messages else ""
        
        # Получаем параметры генерации
        params = self.get_generation_params(max_tokens, temperature)
        
        start_time = time.time()
        
        with self.generate_lock:
            try:
                # Генерируем через MLX
                response = generate(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    prompt=prompt,
                    max_tokens=params["max_tokens"],
                    temp=params["temp"],
                    top_p=params["top_p"],
                )
                
                response_tokens = len(self.tokenizer.encode(response))
                self.generation_stats['total_tokens_generated'] += response_tokens
                    
            except Exception as e:
                if not self._warming_up:
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
            'device': 'mlx',
            'total_requests': self.generation_stats['total_requests'],
            'avg_generation_time_ms': self.generation_stats['avg_generation_time'] * 1000,
            'total_tokens_generated': self.generation_stats['total_tokens_generated'],
            'tokens_per_request': tokens_per_request,
            'model_initialized': self._initialized,
        }
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли модель"""
        return self._initialized

# Глобальный экземпляр для использования в container.py
model_service_mlx = ModelServiceMLX()