# models/dialog.py (изменения в модели Dialog)
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, model_serializer
from datetime import datetime
from typing import List, Optional, Dict, Any

from .enums import MessageRole
from .message import Message
from services.model.thinking_handler import ThinkingHandler


class Dialog(BaseModel):
    """Модель диалога с кэшированием формата для UI и для модели (инкрементальное обновление)"""

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
    visible: bool = Field(default=False)   # <-- новое поле

    # Приватные поля для кэширования UI-формата
    _ui_cache: Optional[List[Dict[str, str]]] = PrivateAttr(default=None)
    _ui_cache_version: int = PrivateAttr(default=-1)

    # Приватные поля для кэширования формата модели
    _model_cache: Optional[List[Dict[str, str]]] = PrivateAttr(default=None)
    _model_cache_version: int = PrivateAttr(default=-1)

    # Счётчик версий истории (увеличивается при любом изменении)
    _history_version: int = PrivateAttr(default=0)

    def model_post_init(self, __context):
        """Инициализация после создания модели (в т.ч. при загрузке из json)."""
        self._history_version = len(self.history)
        self._invalidate_caches()

    def _invalidate_caches(self):
        """Сбрасывает все кэши."""
        self._ui_cache = None
        self._model_cache = None

    def mark_visible(self):
        """Делает диалог видимым в списке (после первого сообщения)."""
        if not self.visible:
            self.visible = True
            self.updated = datetime.now()
            self._invalidate_caches()

    # ========== КОНТЕКСТНЫЕ МЕТОДЫ ==========

    @property
    def context_manager(self):
        from services.context.factory import ContextManagerFactory
        return ContextManagerFactory.get_for_dialog(self)

    def get_context_for_generation(self) -> str:
        return self.context_manager.get_context_for_generation()

    def add_interaction_to_context(self, user_message: str, assistant_message: str):
        self.context_manager.add_interaction(user_message, assistant_message)

    def save_context_state(self):
        return self.context_manager.save_state()

    # ========== МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ ФОРМАТОВ С КЭШИРОВАНИЕМ ==========

    def to_ui_format(self) -> List[Dict[str, str]]:
        if self._ui_cache is not None and self._ui_cache_version == self._history_version:
            return self._ui_cache

        formatted = []
        for msg in self.history:
            content = msg.content
            if msg.role == MessageRole.ASSISTANT:
                content = ThinkingHandler.format_for_ui(content)
            formatted.append({"role": msg.role.value, "content": content})

        self._ui_cache = formatted
        self._ui_cache_version = self._history_version
        return formatted

    def to_model_format(self) -> List[Dict[str, str]]:
        if self._model_cache is not None and self._model_cache_version == self._history_version:
            return self._model_cache

        formatted = [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.history
        ]
        self._model_cache = formatted
        self._model_cache_version = self._history_version
        return formatted

    # ========== МЕТОДЫ, ИЗМЕНЯЮЩИЕ ИСТОРИЮ ==========

    def add_message(self, role: MessageRole, content: str) -> Message:
        """Добавляет сообщение и увеличивает версию истории."""
        message = Message(role=role, content=content)
        self.history.append(message)
        self.updated = datetime.now()
        self._history_version += 1
        return message

    def clear_history(self):
        self.history.clear()
        self.updated = datetime.now()
        self._history_version += 1
        self._invalidate_caches()

    # ========== МЕТОДЫ, НЕ ИЗМЕНЯЮЩИЕ ИСТОРИЮ ==========

    def rename(self, new_name: str):
        self.name = new_name
        self.updated = datetime.now()

    def pin(self, position: int):
        self.pinned = True
        self.pinned_position = position

    def unpin(self):
        self.pinned = False
        self.pinned_position = None

    # ========== СЕРИАЛИЗАЦИЯ ==========

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует диалог в JSON-совместимый словарь."""
        return {
            "id": self.id,
            "name": self.name,
            "history": [msg.to_dict() for msg in self.history],
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "status": self.status,
            "pinned": self.pinned,
            "pinned_position": self.pinned_position,
            "visible": self.visible,           # <-- сохраняем поле
        }

    json_serialize = to_dict