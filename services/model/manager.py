"""
Главный координатор для работы с моделью MLX.
"""
import time
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
import threading
import asyncio
from threading import Lock

from container import container
from .loader import ModelLoader
from .generator import ResponseGenerator
from .parameters import GenerationParameters
from .thinking_handler import ThinkingHandler
from .memory_manager import MLXMemoryManager


class ModelService:
    """Главный сервис для работы с моделями на MLX"""

    def __init__(self):
        self._config = None
        self._initialized = False
        
        # Компоненты (ленивая инициализация)
        self._loader = None
        self._generator = None
        self._parameters = None
        self._thinking_handler = None
        self._memory_manager = None
        
        # Состояние
        self.model = None
        self.tokenizer = None
        self.generate_lock = Lock()
        self._active_stop_event = None  # threading.Event для остановки текущей генерации
        self._stream_lock = threading.Lock()  # Защита от одновременного запуска стримов
        self._streaming_active = False  # Флаг активности стрима
        
        # Кэширование конфигурации
        self._model_config = None
        self._gen_config = None

    @property
    def config(self) -> Dict[str, Any]:
        """Ленивая загрузка конфигурации"""
        if self._config is None:
            self._config = container.get_config()
        return self._config

    @property
    def model_config(self) -> Dict[str, Any]:
        """Конфигурация модели"""
        if self._model_config is None:
            self._model_config = self.config.get("model", {})
        return self._model_config

    @property
    def generation_config(self) -> Dict[str, Any]:
        """Конфигурация генерации"""
        if self._gen_config is None:
            self._gen_config = self.config.get("generation", {})
        return self._gen_config

    @property
    def loader(self):
        """Ленивая инициализация ModelLoader"""
        if self._loader is None:
            self._loader = ModelLoader(self.model_config)
        return self._loader

    @property
    def parameters(self):
        """Ленивая инициализация GenerationParameters"""
        if self._parameters is None:
            self._parameters = GenerationParameters(self.generation_config)
        return self._parameters

    @property
    def thinking_handler(self):
        """Ленивая инициализация ThinkingHandler"""
        if self._thinking_handler is None:
            self._thinking_handler = ThinkingHandler()
        return self._thinking_handler

    @property
    def memory_manager(self):
        """Ленивая инициализация MLXMemoryManager"""
        if self._memory_manager is None:
            self._memory_manager = MLXMemoryManager()
        return self._memory_manager

    @property
    def generator(self):
        """Ленивая инициализация ResponseGenerator"""
        if self._generator is None:
            self._generator = ResponseGenerator()
        return self._generator

    def initialize(self, force_reload: bool = False) -> Tuple[Any, Any, Lock]:
        """Инициализирует модель"""
        if self._initialized and not force_reload:
            return self.model, self.tokenizer, self.generate_lock

        try:
            # 1. Настраиваем память
            self.memory_manager.setup_memory_limit(self.model_config)
            
            # 2. Загружаем модель
            self.model, self.tokenizer = self.loader.load()
            
            if self.model and self.tokenizer:
                self._initialized = True
                
                # 3. Настройка токенизатора
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                self.tokenizer.padding_side = "left"
                
                return self.model, self.tokenizer, self.generate_lock
            else:
                return None, None, self.generate_lock
                
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            import traceback
            traceback.print_exc()
            return None, None, self.generate_lock

    def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None
    ) -> str:
        """Генерирует ответ с учётом параметров"""
        
        if not self._initialized:
            self.initialize()
        
        # Определяем параметры генерации
        params = self.parameters.get_generation_parameters(
            max_tokens=max_tokens,
            temperature=temperature,
            enable_thinking=enable_thinking
        )
        
        # Генерируем ответ
        with self.generate_lock:
            try:
                response_text = self.generator.generate(
                    messages=messages,
                    model=self.model,
                    tokenizer=self.tokenizer,
                    params=params,
                    thinking_handler=self.thinking_handler
                )
                
                return response_text
                
            except Exception as e:
                print(f"❌ Ошибка генерации: {e}")
                return "Извините, произошла ошибка при генерации ответа."

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает базовую информацию о модели"""
        return {
            'backend': 'mlx',
            'model_initialized': self._initialized,
            'model_name': self.model_config.get('name', 'unknown'),
        }

    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли модель"""
        return self._initialized
    
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        stop_event: Optional[threading.Event] = None
    ) -> AsyncGenerator[str, None]:
        """Асинхронно стримит ответ модели по токенам с поддержкой остановки."""
        if not self._initialized:
            self.initialize()

        # Захватываем блокировку, чтобы гарантировать только один активный стрим
        if not self._stream_lock.acquire(blocking=False):
            raise RuntimeError("Генерация уже выполняется. Дождитесь завершения.")

        # Используем переданный stop_event или создаем новый
        if stop_event is None:
            stop_event = threading.Event()

        self._active_stop_event = stop_event
        self._streaming_active = True

        try:
            # 1. Получаем параметры генерации
            params = self.parameters.get_generation_parameters(
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking
            )

            # 2. Форматируем промпт
            prompt = self._format_prompt_for_streaming(messages, params["enable_thinking"])

            # 3. Создаем sampler и logits_processors
            from .generator import create_generation_components
            sampler, logits_processors = create_generation_components(params)

            # 4. Импортируем stream_generate
            from mlx_lm import stream_generate

            # 5. Синхронная функция-генератор с проверкой флага остановки
            def _sync_generator():
                for response in stream_generate(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    prompt=prompt,
                    max_tokens=params["max_tokens"],
                    sampler=sampler,
                    logits_processors=logits_processors
                ):
                    # КРИТИЧЕСКАЯ ПРОВЕРКА: Прерываем генерацию, если установлен флаг
                    if stop_event.is_set():
                        # Логируем для отладки. В продакшене можно убрать.
                        # print("[ModelService] Обнаружен флаг остановки, прерываю генерацию.")
                        break

                    chunk = response.text if hasattr(response, 'text') else str(response)
                    if chunk:
                        yield chunk

            # 6. Запускаем в отдельном потоке
            loop = asyncio.get_event_loop()
            sync_gen = _sync_generator()

            try:
                while True:
                    # Получаем следующий чанк из синхронного генератора в потоке
                    chunk = await loop.run_in_executor(None, next, sync_gen, None)
                    if chunk is None:  # Генератор завершился (естественно или по stop_event)
                        break
                    yield chunk
                    await asyncio.sleep(0)  # Возвращаем управление event loop
            except StopIteration:
                pass
            finally:
                # Гарантируем, что генератор закрыт
                if sync_gen:
                    sync_gen.close()

        finally:
            # Восстанавливаем состояние, даже если была ошибка
            self._streaming_active = False
            self._active_stop_event = None
            self._stream_lock.release()
            # print("[ModelService] Блокировка освобождена, состояние сброшено.")

    def _format_prompt_for_streaming(self, messages: List[Dict[str, str]], enable_thinking: bool) -> str:
        """Форматирует промпт для stream_generate (аналогично generator.py)."""
        try:
            prompt = self.tokenizer.apply_chat_template(
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
            # print("[ModelService] Устанавливаю флаг остановки...")
            self._active_stop_event.set()
        # else:
        #   print("[ModelService] Нет активной генерации для прерывания.")