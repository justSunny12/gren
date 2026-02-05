# /services/model_service.py
import time
import os
import re
from typing import Dict, Any, List, Optional
from threading import Lock
from datetime import datetime
import mlx.core as mx
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler, make_logits_processors

class ModelService:
    """Сервис для работы с моделями на MLX с поддержкой enable_thinking"""

    def __init__(self):
        # Лениво загружаем конфиг и сервисы
        self._config = None
        self.model = None
        self.tokenizer = None
        self.generate_lock = Lock()
        self._initialized = False
        
        # Статистика
        self.generation_stats = {
            'total_requests': 0,
            'avg_generation_time': 0,
            'total_tokens_generated': 0,
            'last_cleanup': datetime.now()
        }

    @property
    def config(self) -> Dict[str, Any]:
        """Ленивая загрузка конфигурации"""
        if self._config is None:
            from container import container
            self._config = container.get_config()
        return self._config

    def _setup_memory_limit(self):
        """Устанавливает лимит памяти для MLX на Apple Silicon"""
        model_config = self.config.get("model", {})
        memory_limit = model_config.get("unified_memory_limit")
        
        if memory_limit and hasattr(mx.metal, 'set_cache_limit'):
            try:
                # Конвертируем MB в байты
                total_memory = mx.device_info().get('memory_size', 0)
                limit_bytes = int(total_memory * 0.8)
                mx.set_cache_limit(limit_bytes)
                print(f"💾 Установлен лимит памяти MLX: {limit_bytes/1024**3:.2f} GB")
            except Exception as e:
                print(f"⚠️ Не удалось установить лимит памяти: {e}")

    def initialize(self, force_reload: bool = False):
        """Инициализирует модель"""
        if self._initialized and not force_reload:
            return self.model, self.tokenizer, self.generate_lock

        model_config = self.config.get("model", {})
        start_time = time.time()

        try:
            # 1. Устанавливаем лимит памяти
            self._setup_memory_limit()
            
            # 2. Определяем путь для загрузки
            local_path = model_config.get("local_path")
            model_name = model_config.get("name", "Qwen/Qwen3-30B-A3B-MLX-4bit")

            # 3. Проверяем локальный путь
            load_path = None
            if local_path and os.path.exists(local_path):
                load_path = local_path
                print(f"📂 Загрузка модели из локального пути: {local_path}")
            elif local_path:
                # Локальный путь указан, но не существует
                print(f"⚠️ Локальный путь не существует: {local_path}")
                print(f"📡 Попытка загрузки из Hugging Face: {model_name}")
                load_path = model_name
            else:
                # Локальный путь не указан - загружаем из HF
                print(f"📡 Загрузка модели из Hugging Face: {model_name}")
                load_path = model_name
            
            # 4. Загружаем модель (исправленный вызов load)
            self.model, self.tokenizer = load(
                model_name
            )

            # Настройка токенизатора
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.padding_side = "left"

            self._initialized = True
            load_time = time.time() - start_time
            print(f"✅ Модель загружена за {load_time:.2f} секунд")
            
            # 5. Если скачали из HF и указан локальный путь - сохраняем локально
            if load_path == model_name and local_path and not os.path.exists(local_path):
                print(f"💾 Сохранение модели в локальный путь: {local_path}")
                self._save_model_locally(local_path)

            return self.model, self.tokenizer, self.generate_lock

        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            import traceback
            traceback.print_exc()
            return None, None, self.generate_lock

    def _save_model_locally(self, local_path: str):
        """Сохраняет модель локально для последующего использования"""
        try:
            os.makedirs(local_path, exist_ok=True)
            
            # Сохраняем модель
            if hasattr(self.model, 'save_pretrained'):
                self.model.save_pretrained(local_path)
            
            # Сохраняем токенизатор
            if hasattr(self.tokenizer, 'save_pretrained'):
                self.tokenizer.save_pretrained(local_path)
            
            print(f"✅ Модель сохранена в: {local_path}")
            
        except Exception as e:
            print(f"⚠️ Не удалось сохранить модель локально: {e}")

    def _get_generation_parameters(
        self, 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Определяет итоговые параметры генерации с учётом конфига и режима"""
        
        gen_config = self.config.get("generation", {})
        thinking_config = gen_config.get("thinking_params", {})
        
        # 1. Определяем режим размышлений
        use_thinking = enable_thinking if enable_thinking is not None \
            else gen_config.get("default_enable_thinking", False)
        
        # 2. Выбираем температуру и top_p в зависимости от режима
        if use_thinking:
            final_temp = temperature if temperature is not None \
                else thinking_config.get("temperature", 0.6)
            final_top_p = thinking_config.get("top_p", 0.95)
        else:
            final_temp = temperature if temperature is not None \
                else gen_config.get("default_temperature", 0.7)
            final_top_p = gen_config.get("default_top_p", 0.8)
        
        # 3. Остальные параметры
        final_max_tokens = max_tokens if max_tokens is not None \
            else gen_config.get("default_max_tokens", 512)
        repetition_penalty = gen_config.get("repetition_penalty", 1.1)
        top_k = gen_config.get("top_k", 40)
        
        return {
            "max_tokens": final_max_tokens,
            "temperature": final_temp,
            "top_p": final_top_p,
            "repetition_penalty": repetition_penalty,
            "top_k": top_k,
            "enable_thinking": use_thinking
        }

    def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None
    ) -> str:
        """Генерирует ответ с учётом параметров из конфига"""
        
        if not self._initialized:
            self.initialize()
        
        self.generation_stats['total_requests'] += 1
        params = self._get_generation_parameters(max_tokens, temperature, enable_thinking)
        
        try:
            # Формируем промпт с учётом enable_thinking
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=params["enable_thinking"]
            )
            
        except Exception as e:
            # Fallback на простую конкатенацию, если apply_chat_template не поддерживает enable_thinking
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            prompt += "\nassistant: "
            if params["enable_thinking"]:
                prompt += "<think>"
        
        # Создаём сэмплер и процессоры на основе параметров
        sampler = make_sampler(
            temp=params["temperature"],
            top_p=params["top_p"],
            top_k=params["top_k"]
        )
        
        logits_processors = make_logits_processors(
            repetition_penalty=params["repetition_penalty"]
        )
        
        # Генерация
        start_time = time.time()
        
        with self.generate_lock:
            try:
                response = generate(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    prompt=prompt,
                    sampler=sampler,
                    logits_processors=logits_processors,
                    max_tokens=params["max_tokens"],
                    verbose=False
                )
                
                # Удаляем возможные остатки тегов размышлений
                response_text = self._clean_thinking_tags(response.strip())
                response_tokens = len(self.tokenizer.encode(response_text))
                self.generation_stats['total_tokens_generated'] += response_tokens
                
            except Exception as e:
                print(f"❌ Ошибка генерации: {e}")
                response_text = "Извините, произошла ошибка при генерации ответа."
        
        generation_time = time.time() - start_time
        
        # Обновляем статистику
        if self.generation_stats['total_requests'] > 1:
            old_avg = self.generation_stats['avg_generation_time']
            new_count = self.generation_stats['total_requests']
            self.generation_stats['avg_generation_time'] = (
                old_avg * (new_count - 1) + generation_time
            ) / new_count
        
        return response_text

    def _clean_thinking_tags(self, text: str) -> str:
        """Форматирует текст размышлений с использованием HTML span"""
        import re
        
        think_pattern = r'<think>(.*?)</think>'
        
        def replace_with_span(match):
            think_text = match.group(1).strip()
            if not think_text:
                return ""
            
            # Разбиваем на строки и каждую строку оборачиваем в span
            lines = think_text.split('\n')
            span_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    span_lines.append(f"<span class='thinking-text'>{line}</span>")
                else:
                    span_lines.append('')
            
            return '\n'.join(span_lines)
        
        text = re.sub(think_pattern, replace_with_span, text, flags=re.DOTALL)
        
        # Удаляем оставшиеся теги
        text = text.replace('<think>', '').replace('</think>', '')
        
        # Убираем множественные пустые строки
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику генерации"""
        if self.generation_stats['total_requests'] > 0:
            tokens_per_request = (
                self.generation_stats['total_tokens_generated'] / 
                self.generation_stats['total_requests']
                if self.generation_stats['total_requests'] > 0 else 0
            )
        else:
            tokens_per_request = 0
        
        return {
            'backend': 'mlx',
            'total_requests': self.generation_stats['total_requests'],
            'avg_generation_time_ms': round(self.generation_stats['avg_generation_time'] * 1000, 2),
            'total_tokens_generated': self.generation_stats['total_tokens_generated'],
            'tokens_per_request': round(tokens_per_request, 2),
            'model_initialized': self._initialized,
        }

    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли модель"""
        return self._initialized