# /models/message.py
from pydantic import BaseModel, Field, ConfigDict
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
    
    def json_serialize(self) -> dict:
        """Конвертирует сообщение в JSON-совместимый словарь"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }
    
    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Переопределяем dict для правильной сериализации"""
        return self.json_serialize()