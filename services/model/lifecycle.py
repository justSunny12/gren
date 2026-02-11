"""
Управление жизненным циклом модели
"""
from typing import Tuple, Optional, Any, Dict
from threading import Lock
import mlx.core as mx

from container import container
from .loader import ModelLoader
from .memory_manager import MLXMemoryManager
from .protocol import IModelLifecycleManager


class ModelLifecycleManager(IModelLifecycleManager):
    """Управляет жизненным циклом модели (инициализация, состояние, очистка)"""
    
    def __init__(self):
        self._config = None
        self._model = None
        self._tokenizer = None
        self._initialized = False
        self._generate_lock = Lock()
        
        # Компоненты
        self._loader = None
        self._memory_manager = None
        
    @property
    def config(self):
        """Ленивая загрузка конфигурации"""
        if self._config is None:
            self._config = container.get_config()
        return self._config
    
    @property
    def model_config(self):
        """Конфигурация модели"""
        return self.config.get("model", {})
    
    def _get_loader(self):
        """Ленивая инициализация загрузчика"""
        if self._loader is None:
            self._loader = ModelLoader(self.model_config)
        return self._loader
    
    def _get_memory_manager(self):
        """Ленивая инициализация менеджера памяти"""
        if self._memory_manager is None:
            self._memory_manager = MLXMemoryManager()
        return self._memory_manager
    
    def initialize(self, force_reload: bool = False) -> Tuple[Any, Any, Lock]:
        """Инициализирует модель, токенизатор и возвращает блокировку"""
        if self._initialized and not force_reload:
            return self._model, self._tokenizer, self._generate_lock
        
        try:
            # 1. Настраиваем память
            memory_manager = self._get_memory_manager()
            memory_manager.setup_memory_limit(self.model_config)
            
            # 2. Загружаем модель
            loader = self._get_loader()
            self._model, self._tokenizer = loader.load()
            
            if self._model and self._tokenizer:
                self._initialized = True
                
                # 3. Настройка токенизатора
                if self._tokenizer.pad_token is None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token
                self._tokenizer.padding_side = "left"
                
                return self._model, self._tokenizer, self._generate_lock
            else:
                return None, None, self._generate_lock
                
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            import traceback
            traceback.print_exc()
            return None, None, self._generate_lock
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли модель"""
        return self._initialized
    
    def get_model_and_tokenizer(self) -> Tuple[Optional[Any], Optional[Any]]:
        """Возвращает модель и токенизатор"""
        if not self._initialized:
            self.initialize()
        return self._model, self._tokenizer
    
    def get_lock(self) -> Lock:
        """Возвращает блокировку для генерации"""
        return self._generate_lock
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус модели"""
        return {
            'initialized': self._initialized,
            'model_name': self.model_config.get('name', 'unknown'),
            'memory_configured': self._memory_manager is not None
        }


# Глобальный экземпляр (можно инжектировать через Container)
model_lifecycle_manager = ModelLifecycleManager()