# models/context/enums.py
from enum import Enum

class ChunkType(str, Enum):
    """Типы чанков контекста"""
    RAW = "raw"                 # Сырое взаимодействие
    L1_SUMMARY = "l1_summary"   # Суммаризация первого уровня
    L2_SUMMARY = "l2_summary"   # Суммаризация второго уровня
    CUMULATIVE = "cumulative"   # Кумулятивная строка