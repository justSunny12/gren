"""
Пакет для работы с моделью MLX
"""

from .manager import ModelService
from .loader import ModelLoader
from .generator import ResponseGenerator
from .parameters import GenerationParameters
from .thinking_handler import ThinkingHandler
from .memory_manager import MLXMemoryManager
from .lifecycle import ModelLifecycleManager, model_lifecycle_manager
from .streamer import StreamManager, stream_manager
from .protocol import (
    IModelLoader,
    IResponseGenerator,
    IStreamManager,
    IModelLifecycleManager,
    IMemoryManager,
    IThinkingHandler,
    IGenerationParameters
)

__all__ = [
    'ModelService',
    'ModelLoader',
    'ResponseGenerator',
    'GenerationParameters',
    'ThinkingHandler',
    'MLXMemoryManager',
    'ModelLifecycleManager',
    'model_lifecycle_manager',
    'StreamManager',
    'stream_manager',
    # Protocols
    'IModelLoader',
    'IResponseGenerator',
    'IStreamManager',
    'IModelLifecycleManager',
    'IMemoryManager',
    'IThinkingHandler',
    'IGenerationParameters',
]