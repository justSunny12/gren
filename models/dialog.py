# models/dialog.py (исправленная версия)
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
from datetime import datetime
from typing import List, Optional, Dict, Any
import hashlib

from .enums import MessageRole
from .message import Message


class Dialog(BaseModel):
    """Модель диалога с кэшированием формата для UI"""
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        arbitrary_types_allowed=True
    )
    
    id: str
    name: str
    history: List[Message] = []
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    status: str = "active"
    pinned: bool = False
    pinned_position: Optional[int] = None
    
    # Приватные поля для кэширования формата UI
    _cached_ui_format: Optional[List[Dict[str, str]]] = PrivateAttr(default=None)
    _history_hash: Optional[str] = PrivateAttr(default=None)
    
    # ========== КОНТЕКСТНЫЕ МЕТОДЫ ==========
    
    @property
    def context_manager(self):
        """Получает менеджер контекста из фабрики (сильная ссылка хранится в фабрике)."""
        from services.context.factory import ContextManagerFactory
        return ContextManagerFactory.get_for_dialog(self)
    
    def get_context_for_generation(self) -> str:
        """Получает контекст для генерации"""
        return self.context_manager.get_context_for_generation()
    
    def add_interaction_to_context(self, user_message: str, assistant_message: str):
        """Добавляет взаимодействие в контекст"""
        self.context_manager.add_interaction(user_message, assistant_message)
        
    def save_context_state(self):
        """Сохраняет состояние контекста диалога"""
        return self.context_manager.save_state()
    
    # ========== ОСНОВНЫЕ МЕТОДЫ С КЭШИРОВАНИЕМ ==========
    
    def to_ui_format(self) -> List[Dict[str, str]]:
        """Конвертирует диалог в формат для UI с кэшированием."""
        current_hash = self._calculate_history_hash()
        
        if (self._cached_ui_format is not None and 
            self._history_hash == current_hash):
            return self._cached_ui_format
        
        formatted = [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.history
        ]
        
        self._cached_ui_format = formatted
        self._history_hash = current_hash
        return formatted
    
    def _calculate_history_hash(self) -> str:
        """Вычисляет быстрый хэш истории для инвалидации кэша."""
        if not self.history:
            return "empty"
        
        if len(self.history) <= 3:
            hash_parts = [str(len(self.history))]
            for msg in self.history:
                content_preview = msg.content[:50] if msg.content else ""
                hash_parts.append(f"{msg.role.value}:{len(msg.content)}:{content_preview}")
            hash_string = "|".join(hash_parts)
            return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
        
        recent = self.history[-3:]
        hash_parts = [
            str(len(self.history)),
            str(self.updated.timestamp())
        ]
        for msg in recent:
            content_len = len(msg.content)
            content_preview = msg.content[:30] if content_len > 0 else ""
            hash_parts.append(f"{msg.role.value}:{content_len}:{content_preview[:30]}")
        
        hash_string = "|".join(hash_parts)
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
    
    def _invalidate_cache(self):
        """Инвалидирует кэш форматирования"""
        self._cached_ui_format = None
        self._history_hash = None
    
    # ========== МЕТОДЫ, ИЗМЕНЯЮЩИЕ ИСТОРИЮ ==========
    
    def add_message(self, role: MessageRole, content: str) -> Message:
        """Добавляет сообщение в диалог и инвалидирует кэш"""
        message = Message(role=role, content=content)
        self.history.append(message)
        self.updated = datetime.now()
        self._invalidate_cache()
        return message
    
    def clear_history(self):
        """Очищает историю диалога и инвалидирует кэш"""
        self.history = []
        self.updated = datetime.now()
        self._invalidate_cache()
    
    # ========== МЕТОДЫ, НЕ ИЗМЕНЯЮЩИЕ ИСТОРИЮ ==========
    
    def rename(self, new_name: str):
        """Переименовывает диалог"""
        self.name = new_name
        self.updated = datetime.now()
    
    def pin(self, position: int):
        """Закрепляет диалог на указанной позиции"""
        self.pinned = True
        self.pinned_position = position
    
    def unpin(self):
        """Открепляет диалог"""
        self.pinned = False
        self.pinned_position = None
    
    # ========== СЕРИАЛИЗАЦИЯ ==========
    
    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        return self.json_serialize()

    def json_serialize(self) -> Dict[str, Any]:
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