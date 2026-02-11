# services/context/summarizers.py
"""
Сервисы суммаризации для многоуровневого управления контекстом
Использует ОДНУ модель MLX для всех уровней суммаризации
"""
import asyncio
import threading
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import re
import os

import mlx.core as mx
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler, make_logits_processors

from container import container


@dataclass
class SummaryResult:
    """Результат суммаризации"""
    summary: str
    original_length: int
    summary_length: int
    compression_ratio: float
    processing_time: float
    success: bool
    error: Optional[str] = None


class BaseSummarizer:
    """
    Базовый класс для суммаризаторов.
    Может работать как с собственной загруженной моделью, так и с общей.
    """
    
    def __init__(
        self,
        model_config: Dict[str, Any],
        config: Dict[str, Any],
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        model_lock: Optional[threading.RLock] = None
    ):
        # Параметры конфигурации (нужны для промптов и fallback-загрузки)
        self.model_name = model_config.get("name", "unknown")
        self.local_path = model_config.get("local_path")
        self.config = config
        
        # --- Разделяем два режима ---
        if model is not None and tokenizer is not None:
            # РЕЖИМ 1: Используем готовую модель (shared)
            self._model = model
            self._tokenizer = tokenizer
            self._model_lock = model_lock if model_lock else threading.RLock()
            self._owns_model = False          # модель не наша, выгружать нельзя
            self._is_loading = False
            self._load_error = None
        else:
            # РЕЖИМ 2: Загружаем свою модель (legacy, для обратной совместимости)
            self._model = None
            self._tokenizer = None
            self._model_lock = threading.RLock()
            self._owns_model = True
            self._is_loading = False
            self._load_error = None
        
        # Параметры генерации по умолчанию (могут переопределяться в summarize)
        summarization_params = config.get("generation_params", {})
        model_type = "l1" if "L1" in self.__class__.__name__ else "l2"
        params = summarization_params.get(model_type, {})
        
        self.max_tokens = params.get("max_tokens", 200)
        self.temperature = params.get("temperature", 0.3)
        self.top_p = params.get("top_p", 0.9)
        self.top_k = params.get("top_k", 40)
        self.repetition_penalty = params.get("repetition_penalty", 1.1)
        
        # Статистика
        self._total_requests = 0
        self._successful_requests = 0
        self._total_processing_time = 0.0
        self._last_used: Optional[float] = None
    
    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None
    
    @property
    def is_loading(self) -> bool:
        return self._is_loading
    
    @property
    def stats(self) -> Dict[str, Any]:
        last_used_iso = None
        if self._last_used:
            try:
                last_used_iso = datetime.fromtimestamp(self._last_used).isoformat()
            except (ValueError, OSError):
                last_used_iso = str(self._last_used)
        return {
            'model_name': self.model_name,
            'is_loaded': self.is_loaded,
            'is_loading': self.is_loading,
            'load_error': self._load_error,
            'owns_model': self._owns_model,
            'total_requests': self._total_requests,
            'successful_requests': self._successful_requests,
            'failed_requests': self._total_requests - self._successful_requests,
            'success_rate': self._successful_requests / max(self._total_requests, 1),
            'avg_processing_time': self._total_processing_time / max(self._successful_requests, 1),
            'last_used': last_used_iso,
            'generation_params': {
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'top_p': self.top_p,
                'top_k': self.top_k,
                'repetition_penalty': self.repetition_penalty,
                'enable_thinking': False
            }
        }
    
    async def load_model(self) -> bool:
        """Загружает модель ТОЛЬКО если она не была передана извне."""
        if not self._owns_model:
            # Уже используем готовую модель, ничего не делаем
            return self.is_loaded
        
        with self._model_lock:
            if self.is_loaded:
                return True
            if self._is_loading:
                while self._is_loading:
                    await asyncio.sleep(0.1)
                return self.is_loaded
            
            self._is_loading = True
            self._load_error = None
            try:
                if not self.local_path:
                    self._load_error = f"Локальный путь не указан для модели {self.model_name}"
                    print(f"❌ {self._load_error}")
                    return False
                if not os.path.exists(self.local_path):
                    self._load_error = f"Локальный путь не существует: {self.local_path}"
                    print(f"❌ {self._load_error}")
                    return False
                
                start_time = time.time()
                self._model, self._tokenizer = load(self.local_path)
                
                if self._tokenizer.pad_token is None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token
                self._tokenizer.padding_side = "left"
                
                load_time = time.time() - start_time
                print(f"   ✅ Модель {self.model_name} загружена за {load_time:.2f} сек")
                return True
                
            except Exception as e:
                error_msg = f"Ошибка загрузки модели {self.model_name} из {self.local_path}: {str(e)}"
                print(f"❌ {error_msg}")
                self._load_error = error_msg
                return False
            finally:
                self._is_loading = False
    
    async def ensure_loaded(self) -> bool:
        """Убеждается, что модель готова к работе."""
        if not self._owns_model:
            # В режиме shared модели всегда должны быть готовы (загружены фабрикой)
            if not self.is_loaded:
                raise RuntimeError(f"Shared model {self.model_name} is not loaded in factory")
            return True
        
        # Собственная загрузка
        if not self.is_loaded and not self.is_loading:
            return await self.load_model()
        elif self.is_loading:
            while self._is_loading:
                await asyncio.sleep(0.1)
            return self.is_loaded
        return True
    
    async def summarize(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        **kwargs
    ) -> SummaryResult:
        """Основной метод суммаризации с реальной моделью."""
        start_time = time.time()
        self._total_requests += 1
        
        try:
            if not await self.ensure_loaded():
                return SummaryResult(
                    summary="",
                    original_length=len(text),
                    summary_length=0,
                    compression_ratio=1.0,
                    processing_time=time.time() - start_time,
                    success=False,
                    error=f"Модель не загружена: {self._load_error}"
                )
            
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            temperature = kwargs.get("temperature", self.temperature)
            top_p = kwargs.get("top_p", self.top_p)
            top_k = kwargs.get("top_k", self.top_k)
            repetition_penalty = kwargs.get("repetition_penalty", self.repetition_penalty)
            enable_thinking = False
            
            system = system_prompt if system_prompt is not None else self._get_system_prompt(**kwargs)
            user = user_prompt if user_prompt is not None else self._get_user_prompt(text, **kwargs)
            
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
            
            try:
                prompt = self._tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=enable_thinking
                )
            except Exception as e:
                prompt = f"<|im_start|>system\n{system}<|im_end|>\n"
                prompt += f"<|im_start|>user\n{user}<|im_end|>\n"
                prompt += f"<|im_start|>assistant\n"
            
            sampler = make_sampler(temp=temperature, top_p=top_p, top_k=top_k)
            logits_processors = make_logits_processors(repetition_penalty=repetition_penalty)
            
            with self._model_lock:
                response = generate(
                    model=self._model,
                    tokenizer=self._tokenizer,
                    prompt=prompt,
                    sampler=sampler,
                    logits_processors=logits_processors,
                    max_tokens=max_tokens,
                    verbose=False
                )
            
            summary_text = self._clean_response(response, prompt)
            processing_time = time.time() - start_time
            compression_ratio = len(text) / max(len(summary_text), 1)
            
            self._successful_requests += 1
            self._total_processing_time += processing_time
            self._last_used = time.time()
            
            return SummaryResult(
                summary=summary_text,
                original_length=len(text),
                summary_length=len(summary_text),
                compression_ratio=compression_ratio,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Ошибка суммаризации: {str(e)}"
            print(f"❌ {error_msg}")
            return SummaryResult(
                summary="",
                original_length=len(text),
                summary_length=0,
                compression_ratio=1.0,
                processing_time=time.time() - start_time,
                success=False,
                error=error_msg
            )
    
    def _clean_response(self, response: str, prompt: str) -> str:
        """Очищает ответ модели от промпта и лишних символов."""
        if response.startswith(prompt):
            response = response[len(prompt):]
        response = response.strip()
        response = response.strip('"\'`')
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        response = response.replace('<think>', '').replace('</think>', '').strip()
        return response
    
    def unload_model(self):
        """Выгружает модель ТОЛЬКО если она принадлежит этому экземпляру."""
        with self._model_lock:
            if self._owns_model and self._model is not None:
                self._model = None
                self._tokenizer = None
                if hasattr(mx, 'clear_cache'):
                    mx.clear_cache()
                print(f"✅ Модель выгружена: {self.model_name}")
            elif not self._owns_model:
                # Игнорируем вызов для shared-модели
                pass
    
    # --- Методы, переопределяемые в наследниках ---
    def _get_system_prompt(self, **kwargs) -> str:
        raise NotImplementedError
    
    def _get_user_prompt(self, text: str, **kwargs) -> str:
        raise NotImplementedError


class L1Summarizer(BaseSummarizer):
    """Суммаризатор первого уровня (подробные конспекты)"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_input_length = self.config.get("l1_chunks", {}).get("max_char_limit", 2000)
    
    def _get_system_prompt(self, **kwargs) -> str:
        return """Ты создаёшь детализированные конспекты диалогов для кратковременной памяти системы.
Твоя задача — сохранить максимум важных деталей, фактов, решений и контекста.

Требования к конспекту:
0. Не пиши заголовков и не форматируй текст
1. Сохрани все ключевые факты, данные, имена, даты, числа
2. Перечисли конкретные решения, действия, инструкции
3. Зафиксируй контекст обсуждения и логические связи
4. Отметь важные выводы и соглашения
5. Сохрани технические детали, команды, параметры если они есть
6. Будь подробным, но избегай повторений
7. Конспект должен быть на языке исходных сообщений

Формат: сплошной связный текст, 5-7 предложений с сохранением существенных деталей."""
    
    def _get_user_prompt(self, text: str, **kwargs) -> str:
        # Простое обрезание, можно улучшить при необходимости
        if len(text) > self.max_input_length:
            text = text[:self.max_input_length] + "...[текст обрезан]"
        return f"""Диалог для конспектирования:

{text}

Создай краткий конспект этого обсуждения, следуя требованиям выше:"""
    
    def _clean_response(self, response: str, prompt: str) -> str:
        cleaned = super()._clean_response(response, prompt)
        if cleaned and not cleaned.startswith("[L1 Summary]"):
            cleaned = f"[L1 Summary] {cleaned}"
        return cleaned


class L2Summarizer(BaseSummarizer):
    """Суммаризатор второго уровня (сжатые обобщения)"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_input_length = self.config.get("l2_summary", {}).get("max_char_limit", 4000)
    
    def _get_system_prompt(self, **kwargs) -> str:
        return """Ты — аналитик истории обсуждений. Твоя задача — создавать сжатые сводные записи на основе нескольких конспектов.

Требования к сводной записи:
0. Не используй заголовки, форматирование и Markdown
1. Сохрани хронологию обсуждаемых тем
2. Выдели ключевые точки развития обсуждения
3. Отметь принятые решения и их эволюцию
4. Покажи связь между разными частями обсуждения
5. Будь максимально сжатым, но сохрани смысловую целостность
6. По возможности предпочитай более краткие формулировки
7. Конспект должен быть на языке исходных сообщений

Формат: краткий связный текст, 2-3 предложения."""
    
    def _get_user_prompt(self, text: str, **kwargs) -> str:
        if len(text) > self.max_input_length:
            text = text[:self.max_input_length] + "...[текст обрезан]"
        return f"""Конспекты частей диалога (в хронологическом порядке):

{text}

Создай сжатую сводную запись, следуя требованиям выше:"""
    
    def _clean_response(self, response: str, prompt: str) -> str:
        cleaned = super()._clean_response(response, prompt)
        if cleaned.startswith("[L1 Summary]"):
            cleaned = cleaned.replace("[L1 Summary]", "[L2 Summary]")
        elif cleaned and not cleaned.startswith("[L2 Summary]"):
            cleaned = f"[L2 Summary] {cleaned}"
        return cleaned.strip()


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
            # Если экземпляры уже созданы — возвращаем
            if "l1" in cls._instances and "l2" in cls._instances:
                return cls._instances.copy()
            
            # Получаем конфигурацию модели (единой)
            model_config = config.get("model", {})
            if not model_config.get("local_path"):
                raise ValueError("В context_config.yaml отсутствует секция model.local_path")
            
            # Загружаем модель ОДИН РАЗ
            if cls._shared_model is None or cls._shared_tokenizer is None:
                cls._load_shared_model(model_config)
            
            # Создаём экземпляры суммаризаторов с общей моделью и блокировкой
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
        """Загружает общую модель и создаёт блокировку."""
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
        """Предзагружает единую модель и создаёт суммаризаторы."""
        with cls._lock:
            if cls._preloaded:
                return True
            
            loading_config = config.get("loading", {})
            if not loading_config.get("preload", True):
                print("ℹ️ Предзагрузка суммаризаторов отключена в конфиге")
                return False
            
            try:
                # Просто вызываем get_all_summarizers — она загрузит модель
                cls.get_all_summarizers(config)
                
                # --- ИСПРАВЛЕНИЕ: правильный запуск корутины прогрева ---
                if loading_config.get("warmup", True):
                    # Получаем или создаём event loop
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Запускаем прогрев и ждём завершения
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
        """Прогревает модель коротким запросом."""
        # print("\n🔥 Прогрев суммаризатора...")
        summarizers = cls.get_all_summarizers({})  # конфиг уже загружен
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
        """Выгружает общую модель (только если она не используется)."""
        with cls._lock:
            # Очищаем ссылки на суммаризаторы
            cls._instances.clear()
            # Выгружаем модель
            if cls._shared_model is not None:
                # MLX не имеет явного метода выгрузки, просто удаляем ссылки
                cls._shared_model = None
                cls._shared_tokenizer = None
                cls._shared_lock = None
                if hasattr(mx, 'clear_cache'):
                    mx.clear_cache()
                print("✅ Единая модель суммаризации выгружена")
            cls._preloaded = False
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Возвращает статистику по суммаризаторам и общей модели."""
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