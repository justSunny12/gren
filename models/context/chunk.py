# models/context/chunk.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List
import hashlib

from .enums import ChunkType


class InteractionChunk(BaseModel):
    """Чанк взаимодействия (уровень L1) - хранит только суммаризацию"""
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        arbitrary_types_allowed=True
    )
    
    id: str = Field(..., description="Уникальный идентификатор чанка")
    summary: str = Field(..., description="Суммаризированный текст")
    original_char_count: int = Field(..., description="Количество символов в исходном тексте")
    summary_char_count: int = Field(..., description="Количество символов в суммаризации")
    created_at: datetime = Field(default_factory=datetime.now, description="Время создания")
    messages_indices: List[int] = Field(default_factory=list, description="Индексы сообщений в исходной истории")
    compression_ratio: float = Field(..., description="Степень сжатия (original_chars / summary_chars)")
    chunk_type: ChunkType = Field(default=ChunkType.L1_SUMMARY, description="Тип чанка")
    
    @classmethod
    def create_from_summary(cls, summary: str, original_char_count: int, message_indices: List[int]) -> "InteractionChunk":
        """Создает чанк из результата суммаризации"""
        summary_chars = len(summary)
        compression_ratio = original_char_count / max(summary_chars, 1)
        
        return cls(
            id=hashlib.md5(summary.encode()).hexdigest()[:16],
            summary=summary,
            original_char_count=original_char_count,
            summary_char_count=summary_chars,
            messages_indices=message_indices,
            compression_ratio=compression_ratio
        )
    
    def model_dump_jsonable(self) -> dict:
        """Возвращает словарь, пригодный для JSON сериализации"""
        data = self.model_dump()
        data['created_at'] = self.created_at.isoformat()
        return data


class L2SummaryBlock(BaseModel):
    """Блок суммаризации второго уровня - хранит только суммаризацию"""
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    id: str = Field(..., description="Уникальный идентификатор блока")
    l1_chunk_ids: List[str] = Field(default_factory=list, description="ID чанков L1, которые были суммаризированы")
    summary: str = Field(..., description="Суммаризированный текст уровня L2")
    summary_char_count: int = Field(..., description="Количество символов в суммаризации L2")
    original_char_count: int = Field(..., description="Общее количество символов в исходных чанках L1")
    created_at: datetime = Field(default_factory=datetime.now, description="Время создания")
    compression_ratio: float = Field(..., description="Степень сжатия (original_chars / summary_chars)")
    chunk_type: ChunkType = Field(default=ChunkType.L2_SUMMARY, description="Тип блока")
    
    @classmethod
    def create_from_summary(cls, chunk_ids: List[str], summary: str, original_char_count: int) -> "L2SummaryBlock":
        """Создает блок L2 из результата суммаризации"""
        summary_chars = len(summary)
        compression_ratio = original_char_count / max(summary_chars, 1)
        
        return cls(
            id=hashlib.md5(summary.encode()).hexdigest()[:16],
            l1_chunk_ids=chunk_ids,
            summary=summary,
            summary_char_count=summary_chars,
            original_char_count=original_char_count,
            compression_ratio=compression_ratio
        )
    
    def model_dump_jsonable(self) -> dict:
        """Возвращает словарь, пригодный для JSON сериализации"""
        data = self.model_dump()
        data['created_at'] = self.created_at.isoformat()
        return data