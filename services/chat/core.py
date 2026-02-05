# services/chat/core.py
"""
Базовые чистые функции для работы с чатом
"""

from typing import Tuple
import re


def validate_message(prompt: str) -> Tuple[bool, str]:
    """Валидация входящего сообщения"""
    if not prompt or not prompt.strip():
        return False, "⚠️ Введите сообщение"
    
    # Проверяем длину сообщения
    if len(prompt.strip()) > 5000:
        return False, "Сообщение слишком длинное (максимум 5000 символов)"
    
    return True, ""


def sanitize_user_input(text: str) -> str:
    """Базовая очистка пользовательского ввода"""
    # Убираем лишние пробелы
    text = ' '.join(text.split())
    
    # Убираем нулевые байты и другие непечатаемые символы (кроме переносов строк)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text.strip()