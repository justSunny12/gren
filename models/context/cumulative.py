# models/context/cumulative.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Dict, Any

from .chunk import L2SummaryBlock


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
        data['last_updated'] = self.last_updated.isoformat()
        for block in data['blocks']:
            if 'added_at' in block and isinstance(block['added_at'], datetime):
                block['added_at'] = block['added_at'].isoformat()
        return data