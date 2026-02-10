# models/dialog.py (исправленная версия - убираем __del__)
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
from datetime import datetime
from typing import List, Optional, Dict, Any
import hashlib
import weakref

from .enums import MessageRole
from .message import Message


class Dialog(BaseModel):
    """Модель диалога с кэшированием формата для UI"""
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        arbitrary_types_allowed=True  # Разрешаем приватные поля
    )
    
    id: str
    name: str
    history: List[Message] = []
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    status: str = "active"
    pinned: bool = False
    pinned_position: Optional[int] = None
    
    # Приватные поля для кэширования
    _cached_ui_format: Optional[List[Dict[str, str]]] = PrivateAttr(default=None)
    _history_hash: Optional[str] = PrivateAttr(default=None)
    _context_manager_ref: Optional[Any] = PrivateAttr(default=None)  # Изменено на ref
    
    # ========== КОНТЕКСТНЫЕ МЕТОДЫ ==========
    
    @property
    def context_manager(self):
        """Ленивое получение менеджера контекста"""
        from services.context.factory import ContextManagerFactory
        
        if self._context_manager_ref is None:
            # Создаем менеджер и сохраняем слабую ссылку
            manager = ContextManagerFactory.get_for_dialog(self)
            self._context_manager_ref = weakref.ref(manager)
            return manager
        
        # Получаем менеджер из слабой ссылки
        manager = self._context_manager_ref()
        if manager is None:
            # Ссылка устарела, создаем новую
            manager = ContextManagerFactory.get_for_dialog(self)
            self._context_manager_ref = weakref.ref(manager)
        
        return manager
    
    def get_context_for_generation(self) -> str:
        """Получает контекст для генерации"""
        return self.context_manager.get_context_for_generation()
    
    def add_interaction_to_context(self, user_message: str, assistant_message: str):
        """Добавляет взаимодействие в контекст"""
        self.context_manager.add_interaction(user_message, assistant_message)
    
    def get_context_stats(self) -> Dict[str, Any]:
        """Получает статистику контекста"""
        return self.context_manager.get_stats()
    
    def save_context_state(self):
        """Сохраняет состояние контекста"""
        return self.context_manager.save_state()
    
    def cleanup_context(self):
        """Очищает контекст при удалении диалога"""
        from services.context.factory import ContextManagerFactory
        ContextManagerFactory.remove_for_dialog(self.id)
        self._context_manager_ref = None
    
    # ========== ОСНОВНЫЕ МЕТОДЫ С КЭШИРОВАНИЕМ ==========
    
    def to_ui_format(self) -> List[Dict[str, str]]:
        """
        Конвертирует диалог в формат для UI с кэшированием.
        
        Возвращает кэшированное значение, если история не изменилась.
        Кэш автоматически инвалидируется при изменении истории.
        """
        current_hash = self._calculate_history_hash()
        
        # Если кэш есть и хэш совпадает - возвращаем кэш
        if (self._cached_ui_format is not None and 
            self._history_hash == current_hash):
            return self._cached_ui_format
        
        # Иначе форматируем заново
        formatted = [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.history
        ]
        
        # Сохраняем в кэш
        self._cached_ui_format = formatted
        self._history_hash = current_hash
        
        return formatted
    
    def _calculate_history_hash(self) -> str:
        """
        Вычисляет быстрый хэш истории для инвалидации кэша.
        Использует только последние сообщения и общую длину.
        """
        if not self.history:
            return "empty"
        
        # Для пустой истории или короткой истории используем быстрый хэш
        if len(self.history) <= 3:
            hash_parts = [str(len(self.history))]
            for msg in self.history:
                # Используем роль, длину содержимого и первые 50 символов
                content_preview = msg.content[:50] if msg.content else ""
                hash_parts.append(f"{msg.role.value}:{len(msg.content)}:{content_preview}")
            hash_string = "|".join(hash_parts)
            return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
        
        # Для длинной истории: используем только последние 3 сообщения + метаданные
        recent = self.history[-3:]
        hash_parts = [
            str(len(self.history)),
            str(self.updated.timestamp())
        ]
        
        for msg in recent:
            # Только основные метрики для скорости
            content_len = len(msg.content)
            content_preview = msg.content[:30] if content_len > 0 else ""
            hash_parts.append(f"{msg.role.value}:{content_len}:{content_preview[:30]}")
        
        hash_string = "|".join(hash_parts)
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
    
    def _invalidate_cache(self):
        """Инвалидирует кэш форматирования"""
        self._cached_ui_format = None
        self._history_hash = None
    
    # ========== МЕТОДЫ, ИЗМЕНЯЮЩИЕ ИСТОРИЮ (ИНВАЛИДИРУЮТ КЭШ) ==========
    
    def add_message(self, role: MessageRole, content: str) -> Message:
        """Добавляет сообщение в диалог и инвалидирует кэш"""
        message = Message(role=role, content=content)
        self.history.append(message)
        self.updated = datetime.now()
        self._invalidate_cache()  # Инвалидируем кэш!
        return message
    
    def clear_history(self):
        """Очищает историю диалога и инвалидирует кэш"""
        self.history = []
        self.updated = datetime.now()
        self._invalidate_cache()  # Инвалидируем кэш!
    
    # ========== МЕТОДЫ, НЕ ИЗМЕНЯЮЩИЕ ИСТОРИЮ (НЕ ИНВАЛИДИРУЮТ КЭШ) ==========
    
    def rename(self, new_name: str):
        """Переименовывает диалог (НЕ инвалидирует кэш истории)"""
        self.name = new_name
        self.updated = datetime.now()
    
    def pin(self, position: int):
        """Закрепляет диалог на указанной позиции (НЕ инвалидирует кэш)"""
        self.pinned = True
        self.pinned_position = position
    
    def unpin(self):
        """Открепляет диалог (НЕ инвалидирует кэш)"""
        self.pinned = False
        self.pinned_position = None
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========
    
    def get_last_message(self) -> Optional[Message]:
        """Получает последнее сообщение в диалоге"""
        if self.history:
            return self.history[-1]
        return None
    
    def get_message_count(self) -> int:
        """Получает количество сообщений"""
        return len(self.history)
    
    def is_cache_valid(self) -> bool:
        """Проверяет, действителен ли кэш"""
        if self._cached_ui_format is None or self._history_hash is None:
            return False
        
        current_hash = self._calculate_history_hash()
        return self._history_hash == current_hash
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Возвращает информацию о кэше для отладки"""
        return {
            "cached": self._cached_ui_format is not None,
            "hash_valid": self.is_cache_valid(),
            "history_length": len(self.history),
            "cache_size": len(self._cached_ui_format) if self._cached_ui_format else 0
        }
    
    # ========== МЕТОДЫ СЕРИАЛИЗАЦИИ ==========
    
    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Переопределяем dict для правильной сериализации"""
        return self.json_serialize()

    def json_serialize(self) -> Dict[str, Any]:
        """Сериализует диалог в JSON-совместимый словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "history": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in self.history
            ],
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "status": self.status,
            "pinned": self.pinned,
            "pinned_position": self.pinned_position
        }