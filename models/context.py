# models/context.py
"""
Модели данных для управления контекстом диалога с многоуровневой суммаризацией
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import hashlib
from dataclasses import dataclass

class ChunkType(str, Enum):
    """Типы чанков контекста"""
    RAW = "raw"                 # Сырое взаимодействие
    L1_SUMMARY = "l1_summary"   # Суммаризация первого уровня
    L2_SUMMARY = "l2_summary"   # Суммаризация второго уровня
    CUMULATIVE = "cumulative"   # Кумулятивная строка


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
        # Конвертируем datetime в строку
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
        # Конвертируем datetime в строку
        data['created_at'] = self.created_at.isoformat()
        return data


class CumulativeContext(BaseModel):
    """Кумулятивная строка P с блоками суммаризации"""
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    content: str = Field(default="", description="Содержимое кумулятивной строки")
    blocks: List[Dict[str, Any]] = Field(default_factory=list, description="Блоки суммаризации L2")
    total_chars: int = Field(default=0, description="Общее количество символов")
    last_updated: datetime = Field(default_factory=datetime.now, description="Время последнего обновления")
    
    def add_block(self, l2_block: L2SummaryBlock):
        """Добавляет блок L2 в кумулятивную строку"""
        block_text = f"<sum_block id='{l2_block.id}'>\n{l2_block.summary}\n</sum_block>\n\n"
        self.content += block_text
        self.total_chars += len(block_text)
        self.blocks.append({
            'id': l2_block.id,
            'chunk_ids': l2_block.l1_chunk_ids,
            'summary': l2_block.summary,
            'summary_chars': l2_block.summary_char_count,
            'original_chars': l2_block.original_char_count,
            'compression_ratio': l2_block.compression_ratio,
            'added_at': datetime.now().isoformat()
        })
        self.last_updated = datetime.now()
    
    def get_formatted(self) -> str:
        """Возвращает отформатированную кумулятивную строку"""
        if not self.content:
            return ""
        return f"# Кумулятивный контекст (история обсуждения):\n{self.content}"
    
    def model_dump_jsonable(self) -> dict:
        """Возвращает словарь, пригодный для JSON сериализации"""
        data = self.model_dump()
        # Конвертируем datetime в строку
        data['last_updated'] = self.last_updated.isoformat()
        # Конвертируем datetime в блоках
        for block in data['blocks']:
            if 'added_at' in block and isinstance(block['added_at'], datetime):
                block['added_at'] = block['added_at'].isoformat()
        return data


class DialogContextState(BaseModel):
    """Полное состояние контекста диалога (только суммаризации)"""
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    # Сырой хвост (последние n символов) - ЕДИНСТВЕННОЕ место, где хранится несуммаризованный текст
    raw_tail: str = Field(default="", description="Сырые последние сообщения")
    raw_tail_char_limit: int = Field(default=2000, description="Лимит символов для сырого хвоста")
    
    # Чанки первого уровня (только суммаризации)
    l1_chunks: List[InteractionChunk] = Field(default_factory=list, description="Чанки суммаризации L1")
    
    # Блоки второго уровня (только суммаризации)
    l2_blocks: List[L2SummaryBlock] = Field(default_factory=list, description="Блоки суммаризации L2")
    
    # Кумулятивная строка
    cumulative_context: CumulativeContext = Field(default_factory=CumulativeContext)
    
    # Параметры суммаризации
    l1_summary_threshold: int = Field(default=4, description="Количество чанков L1 для запуска L2")
    l2_preserve_ratio: float = Field(default=0.5, description="Доля старейших чанков L1 для L2 суммаризации")
    
    # Статистика
    total_interactions: int = Field(default=0, description="Всего взаимодействий")
    total_characters_processed: int = Field(default=0, description="Всего обработано символов")
    total_summarizations_l1: int = Field(default=0, description="Всего L1 суммаризаций")
    total_summarizations_l2: int = Field(default=0, description="Всего L2 суммаризаций")
    last_summarization_time: Optional[datetime] = Field(default=None, description="Время последней суммаризации")
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику контекста"""
        return {
            'total_interactions': self.total_interactions,
            'total_characters_processed': self.total_characters_processed,
            'total_summarizations_l1': self.total_summarizations_l1,
            'total_summarizations_l2': self.total_summarizations_l2,
            'current_raw_tail_chars': len(self.raw_tail),
            'current_l1_chunks': len(self.l1_chunks),
            'current_l2_blocks': len(self.l2_blocks),
            'cumulative_chars': self.cumulative_context.total_chars,
            'compression_ratio_overall': self.total_characters_processed / max(
                len(self.raw_tail) + 
                sum(c.summary_char_count for c in self.l1_chunks) + 
                self.cumulative_context.total_chars, 1
            )
        }
    
    def model_dump_jsonable(self) -> dict:
        """Возвращает словарь, пригодный для JSON сериализации"""
        data = self.model_dump()
        # Конвертируем datetime в строку
        if self.last_summarization_time:
            data['last_summarization_time'] = self.last_summarization_time.isoformat()
        # Конвертируем вложенные объекты
        data['l1_chunks'] = [chunk.model_dump_jsonable() for chunk in self.l1_chunks]
        data['l2_blocks'] = [block.model_dump_jsonable() for block in self.l2_blocks]
        data['cumulative_context'] = self.cumulative_context.model_dump_jsonable()
        return data
    
class MessageInteraction(BaseModel):
    """Взаимодействие: пара сообщений пользователь-ассистент"""
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    user_message: str
    assistant_message: str
    user_timestamp: datetime
    assistant_timestamp: datetime
    message_indices: List[int]  # Индексы в исходной истории
    
    @property
    def text(self) -> str:
        """Текст взаимодействия"""
        return f"Пользователь: {self.user_message}\nАссистент: {self.assistant_message}"
    
    @property
    def char_count(self) -> int:
        """Количество символов"""
        return len(self.text)
    
    @classmethod
    def from_messages(cls, user_msg_index: int, assistant_msg_index: int, 
                      user_msg: Any, assistant_msg: Any) -> "MessageInteraction":
        """Создает взаимодействие из двух сообщений"""
        return cls(
            user_message=user_msg.content,
            assistant_message=assistant_msg.content,
            user_timestamp=user_msg.timestamp,
            assistant_timestamp=assistant_msg.timestamp,
            message_indices=[user_msg_index, assistant_msg_index]
        )
    
    def model_dump_jsonable(self) -> dict:
        """Возвращает словарь, пригодный для JSON сериализации"""
        data = self.model_dump()
        # Конвертируем datetime в строку
        data['user_timestamp'] = self.user_timestamp.isoformat()
        data['assistant_timestamp'] = self.assistant_timestamp.isoformat()
        return data