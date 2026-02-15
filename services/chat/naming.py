# services/chat/naming.py
"""
Генерация и валидация названий чатов
"""
from .formatter import clean_text_for_name, extract_first_sentence, truncate_with_ellipsis

def is_default_name(name: str, config: dict) -> bool:
    """Проверяет, является ли название стандартным"""
    if not name:
        return True
    
    default_name = config.get("dialogs", {}).get("default_name", "Новый чат")
    return default_name in name