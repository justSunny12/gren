# /models/message.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any
from datetime import datetime
from .enums import MessageRole

class Message(BaseModel):
    """Модель сообщения в диалоге"""
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Конвертирует сообщение в JSON-совместимый словарь"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }
    
    # Для обратной совместимости с кодом, который использовал json_serialize
    json_serialize = to_dict