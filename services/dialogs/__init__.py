"""
Пакет для работы с диалогами (полная замена dialog_service.py)
"""

from .manager import DialogManager

# Экспортируем DialogManager как DialogService для обратной совместимости
DialogService = DialogManager

__all__ = [
    'DialogManager',
    'DialogService',  # Псевдоним для обратной совместимости
]