# services/context/summarizers.py
"""
Базовые классы суммаризаторов (L1 и L2).
Фабрика вынесена в summarizer_factory.py.
"""
import re
import time
import os
import asyncio
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass

import mlx.core as mx
from mlx_lm import generate
from mlx_lm.sample_utils import make_sampler, make_logits_processors
from container import container


@dataclass
class SummaryResult:
    """Результат суммаризации."""
    summary: str
    original_length: int
    summary_length: int
    compression_ratio: float
    processing_time: float
    success: bool
    error: Optional[str] = None


class BaseSummarizer:
    """Базовый класс для суммаризаторов."""

    def __init__(
        self,
        model_config: Dict[str, Any],
        config: Dict[str, Any],
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        model_lock: Optional[threading.RLock] = None
    ):
        self.model_name = model_config.get("name", "unknown")
        self.local_path = model_config.get("local_path")
        self.config = config
        self._logger = None

        if model is not None and tokenizer is not None:
            self._model = model
            self._tokenizer = tokenizer
            self._model_lock = model_lock if model_lock else threading.RLock()
            self._owns_model = False
        else:
            self._model = None
            self._tokenizer = None
            self._model_lock = threading.RLock()
            self._owns_model = True

        self._is_loading = False
        self._load_error = None

        summarization_params = config.get("generation_params", {})
        model_type = "l1" if "L1" in self.__class__.__name__ else "l2"
        params = summarization_params.get(model_type, {})

        self.max_tokens = params.get("max_tokens", 200)
        self.temperature = params.get("temperature", 0.3)
        self.top_p = params.get("top_p", 0.9)
        self.top_k = params.get("top_k", 40)
        self.repetition_penalty = params.get("repetition_penalty", 1.1)

        self._total_requests = 0
        self._successful_requests = 0
        self._total_processing_time = 0.0
        self._last_used: Optional[float] = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    @property
    def stats(self) -> Dict[str, Any]:
        from datetime import datetime
        last_used_iso = None
        if self._last_used:
            try:
                last_used_iso = datetime.fromtimestamp(self._last_used).isoformat()
            except (ValueError, OSError):
                last_used_iso = str(self._last_used)
        return {
            'model_name': self.model_name,
            'is_loaded': self.is_loaded,
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
        if not self._owns_model:
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
                    return False
                if not os.path.exists(self.local_path):
                    self._load_error = f"Локальный путь не существует: {self.local_path}"
                    return False

                from mlx_lm import load
                start_time = time.time()
                self._model, self._tokenizer = load(self.local_path)

                if self._tokenizer.pad_token is None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token
                self._tokenizer.padding_side = "left"

                self.logger.info("   ✅ Модель %s загружена за %.2f сек", self.model_name, time.time() - start_time)
                return True
            except Exception as e:
                self._load_error = str(e)
                return False
            finally:
                self._is_loading = False

    async def ensure_loaded(self) -> bool:
        if not self._owns_model:
            if not self.is_loaded:
                raise RuntimeError(f"Shared model {self.model_name} is not loaded")
            return True
        if not self.is_loaded and not self.is_loading:
            return await self.load_model()
        elif self.is_loading:
            while self._is_loading:
                await asyncio.sleep(0.1)
            return self.is_loaded
        return True

    async def summarize(self, text: str, system_prompt: Optional[str] = None,
                        user_prompt: Optional[str] = None, **kwargs) -> SummaryResult:
        start_time = time.time()
        self._total_requests += 1

        try:
            if not await self.ensure_loaded():
                self.logger.error("🔍 summarize: модель не загружена")
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
                self.logger.error("🔍 summarize: ошибка apply_chat_template")
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
            import traceback
            tb_str = traceback.format_exc()
            error_msg = f"Ошибка суммаризации: {str(e)}\n{tb_str}"
            self.logger.error("❌ Исключение в summarize: %s", error_msg)
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
        if response.startswith(prompt):
            response = response[len(prompt):]
        response = response.strip()
        response = response.strip('"\'`')
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        return response

    def unload_model(self):
        with self._model_lock:
            if self._owns_model and self._model is not None:
                self._model = None
                self._tokenizer = None
                if hasattr(mx, 'clear_cache'):
                    mx.clear_cache()

    def _get_system_prompt(self, **kwargs) -> str:
        raise NotImplementedError

    def _get_user_prompt(self, text: str, **kwargs) -> str:
        raise NotImplementedError


class L1Summarizer(BaseSummarizer):
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
        max_input = self.config.get("l1_chunks", {}).get("max_char_limit", 2000)
        if len(text) > max_input:
            text = text[:max_input] + "...[текст обрезан]"
        return f"""Диалог для конспектирования:

{text}

Создай краткий конспект этого обсуждения, следуя требованиям выше:"""

    def _clean_response(self, response: str, prompt: str) -> str:
        cleaned = super()._clean_response(response, prompt)
        if cleaned and not cleaned.startswith("[L1 Summary]"):
            cleaned = f"[L1 Summary] {cleaned}"
        return cleaned


class L2Summarizer(BaseSummarizer):
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
        max_input = self.config.get("l2_summary", {}).get("max_char_limit", 4000)
        if len(text) > max_input:
            text = text[:max_input] + "...[текст обрезан]"
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