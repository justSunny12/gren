# services/chat/formatter.py
"""
Форматирование данных для чата
"""

from typing import List, Dict, Any
import re


def format_history_for_model(history) -> List[Dict[str, str]]:
    """Форматирует историю диалога для передачи модели"""
    return [
        {"role": msg.role.value, "content": msg.content}
        for msg in history
    ]


def format_history_for_ui(history) -> List[Dict[str, str]]:
    """Форматирует историю для отображения в UI"""
    return [
        {"role": msg.role.value, "content": msg.content}
        for msg in history
    ]


def clean_text_for_name(text: str, max_word_length: int = 30) -> str:
    """Очищает текст для использования в названии чата"""
    # Убираем лишние пробелы
    text = ' '.join(text.split())
    
    # Убираем слишком длинные слова
    words = text.split()
    cleaned_words = []
    
    for word in words:
        if len(word) > max_word_length:
            word = word[:max_word_length-3] + "..."
        cleaned_words.append(word)
    
    return ' '.join(cleaned_words).strip()


def extract_first_sentence(text: str, max_length: int = 50) -> str:
    """Извлекает первое предложение из текста"""
    # Находим первое предложение
    match = re.match(r'^[^.!?]*[.!?]', text.strip())
    if match:
        sentence = match.group(0)
    else:
        sentence = text.strip()
    
    # Обрезаем если нужно
    if len(sentence) > max_length:
        sentence = sentence[:max_length-3] + "..."
    
    return sentence


def truncate_with_ellipsis(text: str, max_length: int) -> str:
    """Обрезает текст с добавлением многоточия"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."