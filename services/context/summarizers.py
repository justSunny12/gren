"""
Сервисы суммаризации для многоуровневого управления контекстом
Использует реальные модели MLX
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
import mlx.nn as nn
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
    """Базовый класс для суммаризаторов с загрузкой ТОЛЬКО из локального пути"""
    
    def __init__(self, model_config: Dict[str, Any], config: Dict[str, Any]):
        # Основные параметры модели
        self.model_name = model_config.get("name", "unknown")
        self.local_path = model_config.get("local_path")
        self.config = config
        
        # Состояние модели
        self._model = None
        self._tokenizer = None
        self._model_lock = threading.RLock()
        self._is_loading = False
        self._load_error = None
        
        # Параметры генерации
        summarization_params = config.get("models", {}).get("generation_params", {})
        model_type = "l1" if "1.7B" in self.model_name else "l2"
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
        """Проверяет, загружена ли модель"""
        return self._model is not None and self._tokenizer is not None
    
    @property
    def is_loading(self) -> bool:
        """Проверяет, идет ли загрузка модели"""
        return self._is_loading
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Возвращает статистику суммаризатора"""
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
                'enable_thinking': False  # Всегда false для суммаризации
            }
        }
    
    async def load_model(self) -> bool:
        """Загружает модель ТОЛЬКО из локального пути"""
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
                # Проверяем наличие локального пути
                if not self.local_path:
                    self._load_error = f"Локальный путь не указан для модели {self.model_name}"
                    print(f"❌ {self._load_error}")
                    return False
                
                # Проверяем существование локального пути
                if not os.path.exists(self.local_path):
                    self._load_error = f"Локальный путь не существует: {self.local_path}"
                    print(f"❌ {self._load_error}")
                    return False
                
                print(f"📥 Загрузка модели суммаризации {self.model_name} из context_config.local_path")
                
                start_time = time.time()
                
                # Загружаем модель из локального пути
                self._model, self._tokenizer = load(self.local_path)
                
                # Настраиваем токенизатор
                if self._tokenizer.pad_token is None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token
                self._tokenizer.padding_side = "left"
                
                load_time = time.time() - start_time
                print(f"   ✅ Модель {self.model_name} загружена за {load_time:.2f} сек\n")
                
                return True
                
            except Exception as e:
                error_msg = f"Ошибка загрузки модели {self.model_name} из {self.local_path}: {str(e)}"
                print(f"❌ {error_msg}")
                self._load_error = error_msg
                return False
                
            finally:
                self._is_loading = False
    
    async def ensure_loaded(self) -> bool:
        """Убеждается, что модель загружена"""
        # Проверяем, включена ли предзагрузка в конфиге
        loading_config = self.config.get("models", {}).get("loading", {})
        preload_enabled = loading_config.get("preload", True)
        
        if preload_enabled and not self.is_loaded and not self.is_loading:
            print(f"⚠️ Предзагрузка включена в конфиге, но модель {self.model_name} не загружена.")
        
        # Стандартная логика ленивой загрузки
        if not self.is_loaded and not self.is_loading:
            return await self.load_model()
        elif self.is_loading:
            while self._is_loading:
                await asyncio.sleep(0.1)
            return self.is_loaded
        return True
    
    def _get_system_prompt(self, **kwargs) -> str:
        """Возвращает системный промпт (должен быть переопределен)"""
        raise NotImplementedError("Метод должен быть реализован в подклассе")
    
    def _get_user_prompt(self, text: str, **kwargs) -> str:
        """Возвращает пользовательский промпт (должен быть переопределен)"""
        raise NotImplementedError("Метод должен быть реализован в подклассе")
    
    def _truncate_text(self, text: str, max_chars: int = 4000) -> str:
        # """Обрезает текст до максимальной длины, стараясь не разрывать предложения"""
        # if len(text) <= max_chars:
        #     return text
        
        # # Пытаемся обрезать на границе предложения
        # truncated = text[:max_chars]
        # last_period = truncated.rfind('. ')
        # last_question = truncated.rfind('? ')
        # last_exclamation = truncated.rfind('! ')
        # last_newline = truncated.rfind('\n\n')
        
        # cut_point = max(last_period, last_question, last_exclamation, last_newline)
        # if cut_point > max_chars * 0.7:
        #     return truncated[:cut_point + 1] + "\n...[текст обрезан]..."
        
        # # Иначе обрезаем на границе слова
        # last_space = truncated.rfind(' ')
        # if last_space > max_chars * 0.8:
        #     return truncated[:last_space] + " ...[текст обрезан]"
        
        # return truncated + " ...[текст обрезан]"
        return text
    
    async def summarize(self, text: str, **kwargs) -> SummaryResult:
        """Основной метод суммаризации с реальной моделью"""
        start_time = time.time()
        self._total_requests += 1
        
        try:
            # Проверяем загрузку модели
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
            
            # Получаем параметры генерации
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            temperature = kwargs.get("temperature", self.temperature)
            top_p = kwargs.get("top_p", self.top_p)
            top_k = kwargs.get("top_k", self.top_k)
            repetition_penalty = kwargs.get("repetition_penalty", self.repetition_penalty)
            
            # ВНИМАНИЕ: для суммаризации ВСЕГДА enable_thinking=False
            enable_thinking = False
            
            # Создаем структурированные сообщения
            messages = [
                {"role": "system", "content": self._get_system_prompt(**kwargs)},
                {"role": "user", "content": self._get_user_prompt(text, **kwargs)}
            ]
            
            # Форматируем через apply_chat_template с отключенным thinking
            try:
                prompt = self._tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=enable_thinking  # Всегда False для суммаризации
                )
            except Exception as e:
                # Fallback на наш формат
                print(f"⚠️ Ошибка apply_chat_template: {e}, используем fallback")
                prompt = f"<|im_start|>system\n{self._get_system_prompt(**kwargs)}<|im_end|>\n"
                prompt += f"<|im_start|>user\n{self._get_user_prompt(text, **kwargs)}<|im_end|>\n"
                prompt += f"<|im_start|>assistant\n"
            
            # Создаем сэмплер и процессоры - ВНИМАНИЕ: не передаем enable_thinking!
            sampler = make_sampler(
                temp=temperature,
                top_p=top_p,
                top_k=top_k
            )
            
            logits_processors = make_logits_processors(
                repetition_penalty=repetition_penalty
            )
            
            # Генерируем суммаризацию
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
            
            # Очищаем ответ
            summary_text = self._clean_response(response, prompt)
            
            # Вычисляем метрики
            processing_time = time.time() - start_time
            compression_ratio = len(text) / max(len(summary_text), 1)
            
            # Обновляем статистику
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
        """Очищает ответ модели от промпта и лишних символов"""
        # Удаляем промпт из ответа
        if response.startswith(prompt):
            response = response[len(prompt):]
        
        # Убираем лишние пробелы и переносы
        response = response.strip()
        
        # Убираем кавычки и маркеры если они есть
        response = response.strip('"\'`')
        
        # Удаляем теги <think> и </think> и содержимое между ними
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        
        # Удаляем оставшиеся одиночные теги
        response = response.replace('<think>', '').replace('</think>', '').strip()
        
        return response
    
    def unload_model(self):
        """Выгружает модель из памяти"""
        with self._model_lock:
            self._model = None
            self._tokenizer = None
            # Очищаем кэш MLX
            if hasattr(mx, 'clear_cache'):
                mx.clear_cache()
            print(f"✅ Модель выгружена: {self.model_name}")


class L1Summarizer(BaseSummarizer):
    """Суммаризатор первого уровня (Qwen3-1.7B)"""
    
    def __init__(self, config: Dict[str, Any]):
        model_name = config.get("models", {}).get("l1_summarizer", "Qwen/Qwen3-1.7B-MLX-4bit")
        super().__init__(model_name, config)
        
        # Конфигурация L1
        self.max_input_length = config.get("l1_chunks", {}).get("max_char_limit", 2000)
    
    def _get_system_prompt(self, **kwargs) -> str:
        """Системный промпт для L1 суммаризации"""
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

Формат: сплошной связный текст, 5-7 предложений с сохранением существенных деталей. 
Если конспект укладывается в меньшее количество предложений без опускания критичных деталей - отлично."""
    
    def _get_user_prompt(self, text: str, **kwargs) -> str:
        """Пользовательский промпт для L1 суммаризации"""
        # Обрезаем текст если он слишком длинный
        truncated_text = self._truncate_text(text, self.max_input_length)
        
        return f"""Диалог для конспектирования:

{truncated_text}

Создай краткий конспект этого обсуждения, следуя требованиям выше:"""
    
    def _clean_response(self, response: str, prompt: str) -> str:
        """Очищает ответ L1 суммаризатора"""
        # Убираем промпт из ответа
        if response.startswith(prompt):
            response = response[len(prompt):]
        
        # Убираем лишние пробелы и переносы
        response = response.strip()
        
        # Убираем теги MLX если они есть
        response = response.replace('<|im_start|>', '').replace('<|im_end|>', '').strip()
        
        # Убираем кавычки и маркеры если они есть
        response = response.strip('"\'`')
        
        # Удаляем теги <think> и содержимое между ними (на всякий случай)
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        response = response.replace('<think>', '').replace('</think>', '').strip()
        
        # Добавляем маркер уровня
        if response and not response.startswith("[L1 Summary]"):
            response = f"[L1 Summary] {response}"
        
        return response


class L2Summarizer(BaseSummarizer):
    """Суммаризатор второго уровня (Qwen3-4B)"""
    
    def __init__(self, config: Dict[str, Any]):
        model_name = config.get("models", {}).get("l2_summarizer", "Qwen/Qwen3-4B-MLX-4bit")
        super().__init__(model_name, config)
        
        # Конфигурация L2
        self.max_input_length = config.get("l2_summary", {}).get("max_char_limit", 4000)
    
    def _get_system_prompt(self, **kwargs) -> str:
        """Системный промпт для L2 суммаризации"""
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
        """Пользовательский промпт для L2 суммаризации"""
        # Обрезаем текст если он слишком длинный
        truncated_text = self._truncate_text(text, self.max_input_length)
        
        return f"""Конспекты частей диалога (в хронологическом порядке):

{truncated_text}

Создай сжатую сводную запись, следуя требованиям выше:"""
    
    def _clean_response(self, response: str, prompt: str) -> str:
        """Очищает ответ L2 суммаризатора"""
        # Используем родительский метод очистки
        cleaned = super()._clean_response(response, prompt)
        
        # Если ответ слишком длинный, обрезаем его
        # max_summary_length = 300  # L2 должен быть короче L1
        # if len(cleaned) > max_summary_length:
        #     # Пытаемся обрезать на границе предложения
        #     truncated = cleaned[:max_summary_length]
        #     last_period = truncated.rfind('. ')
        #     if last_period > max_summary_length * 0.7:
        #         cleaned = truncated[:last_period + 1]
        #     else:
        #         cleaned = truncated + "..."
        
        # Заменяем маркер L1 на L2
        if cleaned.startswith("[L1 Summary]"):
            cleaned = cleaned.replace("[L1 Summary]", "[L2 Summary]")
        elif cleaned and not cleaned.startswith("[L2 Summary]"):
            cleaned = f"[L2 Summary] {cleaned}"
        
        return cleaned.strip()


class SummarizerFactory:
    """Фабрика для создания суммаризаторов с поддержкой предзагрузки"""
    
    _instances = {}
    _lock = threading.RLock()
    _preloaded = False  # Флаг предзагрузки
    
    @classmethod
    def get_all_summarizers(cls, config: Dict[str, Any]) -> Dict[str, BaseSummarizer]:
        """Получает все суммаризаторы"""
        with cls._lock:
            if "l1" not in cls._instances:
                l1_config = config.get("models", {}).get("l1_summarizer", {})
                cls._instances["l1"] = L1Summarizer(l1_config, config)
                
            if "l2" not in cls._instances:
                l2_config = config.get("models", {}).get("l2_summarizer", {})
                cls._instances["l2"] = L2Summarizer(l2_config, config)
            
            return cls._instances.copy()
    
    @classmethod
    def validate_model_paths(cls, config: Dict[str, Any]) -> Dict[str, bool]:
        """Проверяет существование локальных путей"""
        results = {}
        
        try:
            models_config = config.get("models", {})
            
            # Проверяем L1
            l1_config = models_config.get("l1_summarizer", {})
            l1_path = l1_config.get("local_path") if isinstance(l1_config, dict) else None
            results["l1"] = l1_path and os.path.exists(l1_path)
            
            # Проверяем L2
            l2_config = models_config.get("l2_summarizer", {})
            l2_path = l2_config.get("local_path") if isinstance(l2_config, dict) else None
            results["l2"] = l2_path and os.path.exists(l2_path)
            
            for name, exists in results.items():
                if exists:
                    pass
                else:
                    print(f"❌ Локальный путь {name} не найден")
                    
        except Exception as e:
            print(f"❌ Ошибка проверки путей моделей: {e}")
            
        return results
    
    @classmethod
    def get_all_summarizers(cls, config: Dict[str, Any]) -> Dict[str, BaseSummarizer]:
        """Получает все суммаризаторы с поддержкой предзагрузки"""
        with cls._lock:
            if "l1" not in cls._instances:
                cls._instances["l1"] = L1Summarizer(config)
            if "l2" not in cls._instances:
                cls._instances["l2"] = L2Summarizer(config)
            
            return cls._instances.copy()
        
    @classmethod
    def preload_summarizers(cls, config: Dict[str, Any]):
        """Предзагружает все модели суммаризации"""
        with cls._lock:
            if cls._preloaded:
                return True
            
            summarizers_config = config.get("summarizers", {})
            if not summarizers_config.get("preload", True):
                print("ℹ️ Предзагрузка суммаризаторов отключена в конфиге")
                return False
            
            print("🚀 Предзагрузка моделей суммаризации...")
            
            try:
                # Получаем суммаризаторы
                summarizers = cls.get_all_summarizers(config)
                
                # Создаем event loop для асинхронной загрузки
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Асинхронно загружаем и прогреваем модели
                async def _preload_all():
                    tasks = []
                    for name, summarizer in summarizers.items():
                        # Загружаем модель
                        if not summarizer.is_loaded and not summarizer.is_loading:
                            tasks.append(summarizer.load_model())
                    
                    # Ждем загрузки всех моделей
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                print(f"❌ Ошибка загрузки модели {list(summarizers.keys())[i]}: {result}")
                    
                    # Прогреваем модели если нужно
                    if summarizers_config.get("warmup", True):
                        await cls._warmup_summarizers(summarizers, summarizers_config)
                
                # Запускаем предзагрузку
                if loop.is_running():
                    # Если loop уже запущен, создаем задачу
                    asyncio.create_task(_preload_all())
                else:
                    # Иначе запускаем синхронно
                    loop.run_until_complete(_preload_all())
                
                cls._preloaded = True
                return True
                
            except Exception as e:
                print(f"❌ Ошибка предзагрузки суммаризаторов: {e}")
                return False
    
    @classmethod
    async def _warmup_summarizers(cls, summarizers: Dict[str, BaseSummarizer], config: Dict[str, Any]):
        """Прогревает модели суммаризации"""
        warmup_text = config.get("warmup_text", "Тестовый текст для прогрева модели суммаризации.")
        print("🔥 Прогрев моделей суммаризации...")
        
        tasks = []
        for name, summarizer in summarizers.items():
            if summarizer.is_loaded:
                # Прогреваем коротким запросом
                tasks.append(
                    summarizer.summarize(
                        warmup_text[:100],  # Короткий текст
                        max_tokens=10,
                        temperature=0.1
                    )
                )
        
        # Запускаем прогрев параллельно
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"⚠️ Ошибка прогрева {list(summarizers.keys())[i]}: {result}")
                elif hasattr(result, 'success') and result.success:
                    print(f"  ✅ Прогрет {list(summarizers.keys())[i]} суммаризатор")
    
    @classmethod
    def is_preloaded(cls) -> bool:
        """Проверяет, были ли модели предзагружены"""
        return cls._preloaded
    
    @classmethod
    def unload_all(cls):
        """Выгружает все суммаризаторы"""
        with cls._lock:
            for summarizer in cls._instances.values():
                summarizer.unload_model()
            cls._instances.clear()
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Возвращает статистику по всем менеджерам с информацией о предзагрузке"""
        with cls._lock:
            stats = {
                'total_managers': len(cls._instances),
                'preloaded': cls._preloaded,
                'managers': {}
            }
            
            for dialog_id, manager in cls._instances.items():
                try:
                    manager_stats = manager.get_stats()
                    # Добавляем информацию о предзагрузке
                    manager_stats['preload_enabled'] = cls._preloaded
                    stats['managers'][dialog_id] = manager_stats
                except Exception as e:
                    stats['managers'][dialog_id] = {'error': str(e)}
            
            return stats