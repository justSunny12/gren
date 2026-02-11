"""
Интерфейсы (Protocols) для компонентов модели
"""

from typing import Protocol, List, Dict, Any, Optional, AsyncGenerator, Tuple
import threading
from typing import Optional as Opt

class IModelLoader(Protocol):
    """Протокол для загрузчика моделей"""
    
    def load(self):
        """Загружает модель и токенизатор"""
        ...

class IResponseGenerator(Protocol):
    """Протокол для генератора ответов"""
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        model,
        tokenizer,
        params: Dict[str, Any],
        thinking_handler=None
    ) -> str:
        """Генерирует ответ модели"""
        ...
    
    def _format_prompt(
        self,
        messages: List[Dict[str, str]],
        tokenizer,
        enable_thinking: bool
    ) -> str:
        """Форматирует промпт для модели"""
        ...

class IStreamManager(Protocol):
    """Протокол для менеджера стриминга"""
    
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        model,
        tokenizer,
        params: Dict[str, Any],
        stop_event: Opt[threading.Event] = None
    ) -> AsyncGenerator[str, None]:
        """Асинхронно стримит ответ модели"""
        ...
    
    async def stream_response_with_context(
        self,
        messages: List[Dict[str, str]],
        model,
        tokenizer,
        params: Dict[str, Any],
        stop_event: Opt[threading.Event] = None
    ) -> AsyncGenerator[Tuple[str, Any, Any], None]:
        """Асинхронно стримит ответ с контекстом"""
        ...
    
    def interrupt_generation(self):
        """Прерывает активную генерацию"""
        ...

class IModelLifecycleManager(Protocol):
    """Протокол для управления жизненным циклом модели"""
    
    def initialize(self, force_reload: bool = False) -> Tuple[Any, Any, threading.Lock]:
        """Инициализирует модель и возвращает (модель, токенизатор, блокировка)"""
        ...
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли модель"""
        ...
    
    def get_model_and_tokenizer(self) -> Tuple[Optional[Any], Optional[Any]]:
        """Возвращает модель и токенизатор"""
        ...
    
    def get_lock(self) -> threading.Lock:
        """Возвращает блокировку для генерации"""
        ...
    
    def cleanup(self):
        """Очищает ресурсы модели"""
        ...

class IMemoryManager(Protocol):
    """Протокол для управления памятью"""
    
    def setup_memory_limit(self, model_config: dict) -> bool:
        """Настраивает лимит памяти"""
        ...

class IThinkingHandler(Protocol):
    """Протокол для обработки размышлений"""
    
    def process(self, text: str) -> str:
        """Обрабатывает теги размышлений"""
        ...

class IGenerationParameters(Protocol):
    """Протокол для параметров генерации"""
    
    def get_generation_parameters(
        self,
        max_tokens: Opt[int] = None,
        temperature: Opt[float] = None,
        enable_thinking: Opt[bool] = None
    ) -> Dict[str, Any]:
        """Возвращает параметры генерации"""
        ...