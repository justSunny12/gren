# services/chat/naming.py
"""
Генерация и валидация названий чатов
"""

from typing import Tuple, Optional
import re
from .formatter import clean_text_for_name, extract_first_sentence, truncate_with_ellipsis


def generate_simple_name(prompt: str, config: dict) -> str:
    """Генерирует простое название чата на основе промпта"""
    chat_naming_config = config.get("chat_naming", {})
    max_length = chat_naming_config.get("max_name_length", 50)
    
    # Очищаем текст
    clean_prompt = clean_text_for_name(prompt)
    
    # Берем первое предложение
    name = extract_first_sentence(clean_prompt, max_length)
    
    # Если получили пустое название
    if not name or not name.strip():
        default_name = config.get("dialogs", {}).get("default_name", "Новый чат")
        return f"{default_name}"
    
    # Дополнительно обрезаем если превышает лимит
    name = truncate_with_ellipsis(name, max_length)
    
    return name

def is_default_name(name: str, config: dict) -> bool:
    """Проверяет, является ли название стандартным"""
    if not name:
        return True
    
    default_name = config.get("dialogs", {}).get("default_name", "Новый чат")
    return default_name in name