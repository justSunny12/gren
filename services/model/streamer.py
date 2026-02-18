"""
Менеджер стриминга ответов модели с поддержкой батчинга
"""
import threading
import asyncio
import time
from typing import List, Dict, Any, Optional, AsyncGenerator, Iterator

from mlx_lm import stream_generate
from mlx_lm.sample_utils import make_sampler, make_logits_processors

from .protocol import IStreamManager
from .fast_batcher import FastBatcher, BatchConfig


class StreamManager(IStreamManager):
    """Менеджер стриминга ответов модели с умным батчингом"""
    
    def __init__(self):
        self._active_stop_event = None
        self._stream_lock = threading.Lock()
        self._streaming_active = False
        self._batch_config = None
        
    def set_batch_config(self, config: Dict[str, Any]):
        """Устанавливает конфигурацию батчинга"""
        if config:
            self._batch_config = BatchConfig(
                min_chars_per_batch=config.get('min_chars_per_batch', 6),
                target_chars_per_batch=config.get('target_chars_per_batch', 16),
                max_chars_per_batch=config.get('max_chars_per_batch', 24),
                min_batch_wait_ms=config.get('min_batch_wait_ms', 20.0),
                max_batch_wait_ms=config.get('max_batch_wait_ms', 60.0),
                adaptive_mode=config.get('adaptive_mode', True),
            )
    
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        model,
        tokenizer,
        params: Dict[str, Any],
        stop_event: Optional[threading.Event] = None
    ) -> AsyncGenerator[str, None]:
        """Асинхронно стримит ответ модели с умным батчингом"""
        
        # Захватываем блокировку
        if not self._stream_lock.acquire(blocking=False):
            raise RuntimeError("Генерация уже выполняется. Дождитесь завершения.")
        
        if stop_event is None:
            stop_event = threading.Event()
        
        self._active_stop_event = stop_event
        self._streaming_active = True
        
        # Инициализируем батчер
        batcher = FastBatcher(self._batch_config)
        batcher.start()
        
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
            
            from container import container
            logger = container.get_logger()
            
            # Создаем синхронный генератор
            def _sync_generator() -> Iterator[str]:
                """Синхронный генератор токенов"""
                try:
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
                except Exception as e:
                    logger.error("Ошибка в синхронном генераторе: %s", e)
            
            # Запускаем синхронный генератор
            sync_gen = _sync_generator()
            
            # Основной цикл обработки с батчингом
            last_yield_time = time.time()
            
            try:
                while not stop_event.is_set():
                    try:
                        # Получаем следующий чанк
                        chunk = next(sync_gen)
                        
                        if chunk:
                            # Добавляем в батчер
                            should_yield = batcher.put(chunk)
                            
                            current_time = time.time()
                            time_since_yield = (current_time - last_yield_time) * 1000
                            
                            # Отправляем батч если:
                            # 1. Батчер говорит что пора
                            # 2. Прошло слишком много времени
                            # 3. Слишком много накопилось (fallback)
                            if (should_yield or 
                                time_since_yield > batcher.config.max_batch_wait_ms or
                                len(batcher.get_current_batch()) >= batcher.config.max_chars_per_batch):
                                
                                batch = batcher.take_batch()
                                if batch:
                                    yield batch
                                    last_yield_time = current_time
                        
                        # Небольшая пауза чтобы не грузить CPU
                        await asyncio.sleep(0)
                        
                    except StopIteration:
                        # Генератор завершился
                        break
                    except Exception as e:
                        print(f"❌ Ошибка при получении чанка: {e}")
                        break
                
                # Отправляем остатки после завершения генерации
                final_batch = batcher.take_batch()
                if final_batch:
                    yield final_batch
            
            finally:
                # Закрываем генератор
                try:
                    sync_gen.close()
                except:
                    pass
        
        except Exception as e:
            logger.error("Критическая ошибка в stream_response: %s", e)
            raise
        
        finally:
            # Всегда останавливаем батчер и освобождаем ресурсы
            batcher.stop()
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
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус стриминга"""
        return {
            'streaming_active': self._streaming_active,
            'has_stop_event': self._active_stop_event is not None,
            'batch_config': self._batch_config.__dict__ if self._batch_config else None
        }


# Глобальный экземпляр
stream_manager = StreamManager()