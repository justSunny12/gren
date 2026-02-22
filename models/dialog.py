# models/dialog.py
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
from datetime import datetime
from typing import List, Optional, Dict, Any

from .enums import MessageRole
from .message import Message


class Dialog(BaseModel):
    """Модель диалога с кэшированием формата для UI (инкрементальное обновление)"""

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

    # Приватные поля для кэширования UI-формата
    _ui_cache: Optional[List[Dict[str, str]]] = PrivateAttr(default=None)
    _history_version: int = PrivateAttr(default=0)      # версия истории (увеличивается при любых изменениях)
    _cache_version: int = PrivateAttr(default=0)        # версия, соответствующая текущему кэшу

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

    # ========== ОСНОВНЫЕ МЕТОДЫ С КЭШИРОВАНИЕМ ==========

    def to_ui_format(self) -> List[Dict[str, str]]:
        """Возвращает историю в формате для UI с использованием кэша."""
        # Если кэш актуален — возвращаем его
        if self._ui_cache is not None and self._cache_version == self._history_version:
            return self._ui_cache

        # Иначе строим заново
        formatted = [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.history
        ]
        self._ui_cache = formatted
        self._cache_version = self._history_version
        return formatted

    # ========== МЕТОДЫ, ИЗМЕНЯЮЩИЕ ИСТОРИЮ ==========

    def add_message(self, role: MessageRole, content: str) -> Message:
        """Добавляет сообщение с инкрементальным обновлением кэша."""
        message = Message(role=role, content=content)
        self.history.append(message)
        self.updated = datetime.now()
        self._history_version += 1

        # Если кэш уже существует, просто дополняем его
        if self._ui_cache is not None:
            self._ui_cache.append({"role": role.value, "content": content})
            self._cache_version = self._history_version
        # Иначе кэш остаётся None, будет построен при первом запросе

        return message

    def clear_history(self):
        """Очищает историю, сбрасывая кэш."""
        self.history.clear()
        self.updated = datetime.now()
        self._history_version += 1
        self._ui_cache = None        # кэш больше не актуален
        # _cache_version можно не менять, так как при следующем to_ui_format он перестроится

    # ========== МЕТОДЫ, НЕ ИЗМЕНЯЮЩИЕ ИСТОРИЮ ==========

    def rename(self, new_name: str):
        self.name = new_name
        self.updated = datetime.now()
        # история не меняется — версию и кэш не трогаем

    def pin(self, position: int):
        self.pinned = True
        self.pinned_position = position
        # аналогично

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
            "pinned_position": self.pinned_position
        }

    # Для обратной совместимости
    json_serialize = to_dict