"""
Главный координатор для работы с моделью MLX.
Использует компоненты с четким разделением ответственности.
"""
import threading
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple

from container import container
from .protocol import (
    IModelLifecycleManager,
    IResponseGenerator,
    IStreamManager,
    IThinkingHandler,
    IGenerationParameters
)
from .loader import ModelLoader
from .generator import ResponseGenerator
from .parameters import GenerationParameters
from .thinking_handler import ThinkingHandler
from .memory_manager import MLXMemoryManager
from .lifecycle import model_lifecycle_manager
from .streamer import stream_manager


class ModelService:
    """
    Главный сервис для работы с моделями на MLX.
    Координирует работу компонентов, не содержит бизнес-логики.
    """

    def __init__(self):
        self._config = None
        
        # Внедренные зависимости
        self.lifecycle_manager: IModelLifecycleManager = model_lifecycle_manager
        self.stream_manager: IStreamManager = stream_manager
        
        # Компоненты (ленивая инициализация)
        self._loader = None
        self._generator = None
        self._parameters = None
        self._thinking_handler = None
        self._memory_manager = None

    @property
    def config(self) -> Dict[str, Any]:
        """Ленивая загрузка конфигурации"""
        if self._config is None:
            self._config = container.get_config()
            # Настраиваем батчинг при первой загрузке конфига
            self._setup_batching()
        return self._config
    
    def _setup_batching(self):
        """Настраивает параметры батчинга"""
        stream_batching_config = self._config.get("stream_batching")
        if stream_batching_config:
            self.stream_manager.set_batch_config(stream_batching_config)

    @property
    def model_config(self) -> Dict[str, Any]:
        """Конфигурация модели"""
        return self.config.get("model", {})

    @property
    def generation_config(self) -> Dict[str, Any]:
        """Конфигурация генерации"""
        return self.config.get("generation", {})

    @property
    def loader(self):
        """Ленивая инициализация ModelLoader"""
        if self._loader is None:
            self._loader = ModelLoader(self.model_config)
        return self._loader

    @property
    def parameters(self) -> IGenerationParameters:
        """Ленивая инициализация GenerationParameters"""
        if self._parameters is None:
            self._parameters = GenerationParameters(self.generation_config)
        return self._parameters

    @property
    def thinking_handler(self) -> IThinkingHandler:
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
    def generator(self) -> IResponseGenerator:
        """Ленивая инициализация ResponseGenerator"""
        if self._generator is None:
            self._generator = ResponseGenerator()
        return self._generator

    def get_tokenizer(self):
        """Возвращает токенизатор текущей модели"""
        _, tokenizer = self.lifecycle_manager.get_model_and_tokenizer()
        return tokenizer

    def initialize(self, force_reload: bool = False) -> Tuple[Any, Any, threading.Lock]:
        """Инициализирует модель через LifecycleManager"""
        return self.lifecycle_manager.initialize(force_reload)

    def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None
    ) -> str:
        """Генерирует ответ с учётом параметров"""
        
        # Убеждаемся, что модель инициализирована
        model, tokenizer = self.lifecycle_manager.get_model_and_tokenizer()
        if not model or not tokenizer:
            self.lifecycle_manager.initialize()
            model, tokenizer = self.lifecycle_manager.get_model_and_tokenizer()
        
        # Определяем параметры генерации
        params = self.parameters.get_generation_parameters(
            max_tokens=max_tokens,
            temperature=temperature,
            enable_thinking=enable_thinking
        )
        
        # Получаем блокировку
        generate_lock = self.lifecycle_manager.get_lock()
        
        # Генерируем ответ с блокировкой
        with generate_lock:
            try:
                response_text = self.generator.generate(
                    messages=messages,
                    model=model,
                    tokenizer=tokenizer,
                    params=params,
                    thinking_handler=self.thinking_handler
                )
                
                return response_text
                
            except Exception as e:
                print(f"❌ Ошибка генерации: {e}")
                return "Извините, произошла ошибка при генерации ответа."

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        stop_event: Optional[threading.Event] = None
    ) -> AsyncGenerator[str, None]:
        """Асинхронно стримит ответ модели с умным батчингом (только чанки)"""
        
        # Убеждаемся, что модель инициализирована
        model, tokenizer = self.lifecycle_manager.get_model_and_tokenizer()
        if not model or not tokenizer:
            self.lifecycle_manager.initialize()
            model, tokenizer = self.lifecycle_manager.get_model_and_tokenizer()
        
        # Определяем параметры генерации
        params = self.parameters.get_generation_parameters(
            max_tokens=max_tokens,
            temperature=temperature,
            enable_thinking=enable_thinking
        )
        
        # Делегируем стриминг StreamManager с батчингом
        async for batch in self.stream_manager.stream_response(
            messages=messages,
            model=model,
            tokenizer=tokenizer,
            params=params,
            stop_event=stop_event
        ):
            yield batch

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику модели"""
        lifecycle_status = self.lifecycle_manager.get_status()
        stream_status = self.stream_manager.get_status()
        
        return {
            'backend': 'mlx',
            **lifecycle_status,
            **stream_status,
        }

    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли модель"""
        return self.lifecycle_manager.is_initialized()