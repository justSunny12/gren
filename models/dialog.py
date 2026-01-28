# /models/dialog.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional, Dict, Any
from .enums import MessageRole
from .message import Message

class Dialog(BaseModel):
    """Модель диалога"""
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    id: str
    name: str
    history: List[Message] = []
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    status: str = "active"
    pinned: bool = False  # ← НОВОЕ ПОЛЕ для закрепления
    pinned_position: Optional[int] = None  # ← ПОЗИЦИЯ в закрепленных (чем меньше, тем выше)
    
    def pin(self, position: int):
        """Закрепляет диалог на указанной позиции"""
        self.pinned = True
        self.pinned_position = position
        # Не обновляем updated!
    
    def unpin(self):
        """Открепляет диалог"""
        self.pinned = False
        self.pinned_position = None
    
    def add_message(self, role: MessageRole, content: str) -> Message:
        """Добавляет сообщение в диалог и возвращает его"""
        message = Message(role=role, content=content)
        self.history.append(message)
        self.updated = datetime.now()
        return message
    
    def clear_history(self):
        """Очищает историю диалога"""
        self.history = []
        self.updated = datetime.now()
    
    def rename(self, new_name: str):
        """Переименовывает диалог"""
        self.name = new_name
        self.updated = datetime.now()
    
    def get_last_message(self) -> Optional[Message]:
        """Получает последнее сообщение в диалоге"""
        if self.history:
            return self.history[-1]
        return None
    
    def get_message_count(self) -> int:
        """Получает количество сообщений"""
        return len(self.history)
    
    def to_ui_format(self) -> List[Dict[str, str]]:
        """Конвертирует диалог в формат для UI (Gradio Chatbot)"""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.history
        ]
    
    def get_summary(self, max_length: int = 100) -> str:
        """Получает краткое описание диалога"""
        if not self.history:
            return "Пустой диалог"
        
        # Пытаемся взять последнее сообщение пользователя
        for msg in reversed(self.history):
            if msg.role == MessageRole.USER:
                content = msg.content
                if len(content) > max_length:
                    return content[:max_length] + "..."
                return content
        
        # Если нет сообщений пользователя, берем любое
        last_msg = self.history[-1]
        content = last_msg.content
        if len(content) > max_length:
            return content[:max_length] + "..."
        return content
    
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