"""
Пакет для работы с моделью MLX
"""

from .manager import ModelService
from .loader import ModelLoader
from .parameters import GenerationParameters
from .thinking_handler import ThinkingHandler
from .memory_manager import MLXMemoryManager
from .lifecycle import ModelLifecycleManager, model_lifecycle_manager
from .streamer import StreamManager, stream_manager
from .fast_batcher import FastBatcher, BatchConfig  # НОВОЕ: экспорт батчера
from .protocol import (
    IModelLoader,
    IStreamManager,
    IModelLifecycleManager,
    IMemoryManager,
    IThinkingHandler,
    IGenerationParameters
)

__all__ = [
    'ModelService',
    'model_lifecycle_manager',
    'stream_manager',
    # Protocols
    'IModelLoader',
    'IStreamManager',
    'IModelLifecycleManager',
    'IMemoryManager',
    'IThinkingHandler',
    'IGenerationParameters',
]