# models/context/state.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Dict, Any, Optional

from .enums import ChunkType
from .chunk import InteractionChunk, L2SummaryBlock
from .cumulative import CumulativeContext


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
        if self.last_summarization_time:
            data['last_summarization_time'] = self.last_summarization_time.isoformat()
        data['l1_chunks'] = [chunk.model_dump_jsonable() for chunk in self.l1_chunks]
        data['l2_blocks'] = [block.model_dump_jsonable() for block in self.l2_blocks]
        data['cumulative_context'] = self.cumulative_context.model_dump_jsonable()
        return data