"""
Менеджер стриминга ответов модели
"""
import threading
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple

from mlx_lm import stream_generate
from mlx_lm.sample_utils import make_sampler, make_logits_processors

from .protocol import IStreamManager


class StreamManager(IStreamManager):
    """Менеджер стриминга ответов модели"""
    
    def __init__(self):
        self._active_stop_event = None
        self._stream_lock = threading.Lock()
        self._streaming_active = False
    
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        model,
        tokenizer,
        params: Dict[str, Any],
        stop_event: Optional[threading.Event] = None
    ) -> AsyncGenerator[str, None]:
        """Асинхронно стримит ответ модели по токенам"""
        
        # Захватываем блокировку
        if not self._stream_lock.acquire(blocking=False):
            raise RuntimeError("Генерация уже выполняется. Дождитесь завершения.")
        
        if stop_event is None:
            stop_event = threading.Event()
        
        self._active_stop_event = stop_event
        self._streaming_active = True
        
        try:
            # Форматируем промпт
            prompt = self._format_prompt_for_streaming(
                messages, tokenizer, params["enable_thinking"]
            )
            
            # Создаем sampler и logits_processors
            sampler = make_sampler(
                temp=params["temperature"],
                top_p=params["top_p"],
                top_k=params["top_k"]
            )
            
            logits_processors = make_logits_processors(
                repetition_penalty=params["repetition_penalty"]
            )
            
            # Синхронная функция-генератор
            def _sync_generator():
                for response in stream_generate(
                    model=model,
                    tokenizer=tokenizer,
                    prompt=prompt,
                    max_tokens=params["max_tokens"],
                    sampler=sampler,
                    logits_processors=logits_processors
                ):
                    if stop_event.is_set():
                        break
                    
                    chunk = response.text if hasattr(response, 'text') else str(response)
                    if chunk:
                        yield chunk
            
            # Запускаем в отдельном потоке
            import asyncio
            loop = asyncio.get_event_loop()
            sync_gen = _sync_generator()
            
            try:
                while True:
                    chunk = await loop.run_in_executor(None, next, sync_gen, None)
                    if chunk is None:
                        break
                    yield chunk
                    await asyncio.sleep(0)
            except StopIteration:
                pass
            finally:
                if sync_gen:
                    sync_gen.close()
                    
        finally:
            self._streaming_active = False
            self._active_stop_event = None
            self._stream_lock.release()
    
    def _format_prompt_for_streaming(
        self, 
        messages: List[Dict[str, str]], 
        tokenizer,
        enable_thinking: bool
    ) -> str:
        """Форматирует промпт для stream_generate"""
        try:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=enable_thinking
            )
            return prompt
        except Exception:
            # Fallback
            prompt_lines = [f"{m['role']}: {m['content']}" for m in messages]
            prompt = "\n".join(prompt_lines) + "\nassistant: "
            if enable_thinking:
                prompt += "<think>"
            return prompt
    
    def interrupt_generation(self):
        """Внешний метод для прерывания текущей генерации."""
        if self._active_stop_event and not self._active_stop_event.is_set():
            self._active_stop_event.set()
    
    def is_streaming_active(self) -> bool:
        """Проверяет, активен ли стриминг"""
        return self._streaming_active
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус стриминга"""
        return {
            'streaming_active': self._streaming_active,
            'has_stop_event': self._active_stop_event is not None
        }


# Глобальный экземпляр
stream_manager = StreamManager()