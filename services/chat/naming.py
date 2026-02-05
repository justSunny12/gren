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


def validate_chat_name(name: str, config: dict) -> Tuple[bool, str]:
    """Валидирует название чата"""
    if not name:
        return False, "Название не может быть пустым"
    
    name = name.strip()
    chat_naming_config = config.get("chat_naming", {})
    name_validation = chat_naming_config.get("name_validation", {})
    
    # Проверка минимальной длины
    min_length = chat_naming_config.get("min_name_length", 1)
    if len(name) < min_length:
        return False, f"Название должно быть не короче {min_length} символа"
    
    # Проверка на только пробелы
    if not name_validation.get("allow_whitespace_only", True) and name.isspace():
        return False, "Название не может состоять только из пробелов"
    
    # Проверка максимальной длины
    max_length = chat_naming_config.get("max_name_length", 50)
    if len(name) > max_length:
        return False, f"Название не должно превышать {max_length} символов"
    
    # Проверка на специальные символы
    if not name_validation.get("allow_special_chars", True):
        if re.search(r'[^\w\sА-Яа-яЁё\-.,!?]', name):
            return False, "Название содержит запрещенные символы"
    
    # Проверка процента специальных символов
    max_special_percent = name_validation.get("max_special_chars_percent", 30)
    if max_special_percent < 100:
        special_chars = re.findall(r'[^\w\sА-Яа-яЁё]', name)
        if special_chars:
            special_percent = (len(special_chars) / len(name)) * 100
            if special_percent > max_special_percent:
                return False, f"Слишком много специальных символов ({special_percent:.0f}%)"
    
    return True, ""


def is_default_name(name: str, config: dict) -> bool:
    """Проверяет, является ли название стандартным"""
    if not name:
        return True
    
    default_name = config.get("dialogs", {}).get("default_name", "Новый чат")
    return default_name in name