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
    if len(prompt.strip()) > 30000:
        return False, "Запрос слишком длинный. Для обработки текстов длиннее 30.000 символов воспользуйтесь вложениями"
    return True, ""


def sanitize_user_input(text: str) -> str:
    """Базовая очистка пользовательского ввода.

    Удаляет управляющие символы и схлопывает горизонтальные пробелы,
    сохраняя при этом переносы строк (\n) для многострочных сообщений.
    """
    # Удаляем управляющие символы кроме \n и \r
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Схлопываем горизонтальные пробелы/табы (но не \n) в один пробел
    text = re.sub(r'[ \t]+', ' ', text)
    # Нормализуем \r\n → \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.strip()