# services/context/utils.py (исправленная версия)
"""
Утилиты для работы с контекстом
"""
import re
import hashlib
from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import datetime

# Вместо импорта MessageInteraction, создаем простую структуру
from dataclasses import dataclass
from typing import List as TypingList


@dataclass
class SimpleInteraction:
    """Упрощенная версия взаимодействия для работы в утилитах"""
    user_message: str
    assistant_message: str
    message_indices: TypingList[int] = None
    
    def __post_init__(self):
        if self.message_indices is None:
            self.message_indices = []
    
    @property
    def text(self) -> str:
        """Текст взаимодействия"""
        return f"Пользователь: {self.user_message}\nАссистент: {self.assistant_message}"
    
    @property
    def char_count(self) -> int:
        """Количество символов"""
        return len(self.text)


def split_interaction_by_sentences(text: str, max_chars: int) -> List[str]:
    """
    Разбивает текст на предложения, но не разбивает взаимодействия.
    
    УСТАРЕВШЕЕ: Эта функция не подходит для наших требований.
    Сохраняем для обратной совместимости.
    """
    if len(text) <= max_chars:
        return [text]
    
    # Разделяем по взаимодействиям (пары пользователь-ассистент)
    interactions = []
    current_interaction = []
    lines = text.strip().split('\n')
    
    for line in lines:
        if line.startswith("Пользователь:") and current_interaction:
            # Начинается новое взаимодействие
            interactions.append('\n'.join(current_interaction))
            current_interaction = [line]
        else:
            current_interaction.append(line)
    
    if current_interaction:
        interactions.append('\n'.join(current_interaction))
    
    # Если отдельное взаимодействие превышает max_chars, оставляем его целиком
    result = []
    for interaction in interactions:
        if len(interaction) > max_chars:
            # Взаимодействие слишком большое, но не разбиваем его
            result.append(interaction)
        else:
            result.append(interaction)
    
    return result


def parse_text_to_interactions(text: str) -> List[SimpleInteraction]:
    """
    Парсит текст на взаимодействия пользователь-ассистент.
    Корректно обрабатывает многострочные сообщения с абзацами.
    
    Формат взаимодействия:
    Пользователь: <сообщение>
    Ассистент: <сообщение>
    
    Сообщение может быть многострочным, содержать пустые строки и абзацы.
    """
    interactions = []
    
    # Используем регулярное выражение для поиска пар "Пользователь: ..." и "Ассистент: ..."
    # (?s) - точка соответствует всем символам, включая перенос строки
    pattern = r'Пользователь:\s*(.*?)\nАссистент:\s*(.*?)(?=\n\nПользователь:|\Z)'
    
    matches = re.findall(pattern, text, re.DOTALL)
    
    for user_text, assistant_text in matches:
        # Очищаем текст от лишних пробелов
        user_text = user_text.strip()
        assistant_text = assistant_text.strip()
        
        if user_text and assistant_text:
            interactions.append(SimpleInteraction(
                user_message=user_text,
                assistant_message=assistant_text
            ))
    
    # Если не нашли через регулярку, пробуем более простой метод
    if not interactions:
        lines = text.strip().split('\n')
        current_user = None
        current_assistant = None
        in_assistant_block = False
        
        for line in lines:
            if line.startswith("Пользователь:"):
                # Если уже есть собранное взаимодействие, сохраняем его
                if current_user is not None and current_assistant is not None:
                    interactions.append(SimpleInteraction(
                        user_message=current_user,
                        assistant_message=current_assistant
                    ))
                
                # Начинаем новое взаимодействие
                current_user = line[len("Пользователь:"):].strip()
                current_assistant = ""
                in_assistant_block = False
                
            elif line.startswith("Ассистент:"):
                current_assistant = line[len("Ассистент:"):].strip()
                in_assistant_block = True
                
            elif in_assistant_block and current_assistant is not None:
                # Добавляем строку к сообщению ассистента (включая пустые строки)
                current_assistant += "\n" + line
            elif current_user is not None and not line.startswith("Ассистент:"):
                # Продолжение сообщения пользователя (если оно многострочное)
                current_user += "\n" + line
        
        # Добавляем последнее взаимодействие
        if current_user is not None and current_assistant is not None:
            interactions.append(SimpleInteraction(
                user_message=current_user,
                assistant_message=current_assistant
            ))
    
    return interactions


def group_interactions_into_chunks(
    interactions: List[SimpleInteraction], 
    target_chars: int,
    allow_overflow: bool = True  # Новый параметр
) -> List[List[SimpleInteraction]]:
    """
    Группирует взаимодействия в чанки с учетом разрешения переполнения.
    
    Args:
        allow_overflow: Если True, разрешает переполнение чанка,
                       если он состоит из одного большого взаимодействия
    """
    chunks = []
    current_chunk = []
    current_size = 0
    
    for interaction in interactions:
        interaction_size = interaction.char_count
        
        # ПРАВИЛО 1: Разрешить переполнение одним большим взаимодействием
        if allow_overflow and interaction_size > target_chars:
            # Если чанк пустой, разрешаем переполнение
            if not current_chunk:
                chunks.append([interaction])
                print(f"✅ Разрешено переполнение чанка: "
                      f"{interaction_size} > {target_chars} символов "
                      f"(одно большое взаимодействие)")
                continue
            else:
                # Если чанк не пустой, сохраняем его и начинаем новый
                chunks.append(current_chunk.copy())
                current_chunk = [interaction]
                current_size = interaction_size
                print(f"✅ Создан переполненный чанк: "
                      f"{interaction_size} символов")
                continue
        
        # ПРАВИЛО 2: Стандартная группировка для обычных взаимодействий
        if current_size + interaction_size <= target_chars:
            current_chunk.append(interaction)
            current_size += interaction_size
        else:
            # Начинаем новый чанк
            if current_chunk:
                chunks.append(current_chunk.copy())
            
            current_chunk = [interaction]
            current_size = interaction_size
    
    # Добавляем последний чанк
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def calculate_compression_ratio(original: str, summary: str) -> float:
    """Вычисляет степень сжатия текста"""
    if not summary:
        return 1.0
    return len(original) / len(summary)


def estimate_tokens(text: str, chars_per_token: float = 3.5) -> int:
    """Оценивает количество токенов в тексте"""
    return int(len(text) / chars_per_token)


def format_context_for_model(context_parts: Dict[str, str]) -> str:
    """
    Форматирует контекст для передачи модели
    
    Args:
        context_parts: Словарь с частями контекста
            - cumulative: кумулятивная строка
            - l1_summaries: суммаризации L1
            - raw_tail: сырой хвост
    
    Returns:
        Отформатированный контекст
    """
    parts = []
    
    # Системное сообщение
    system_msg = """Ты получаешь контекст диалога в нескольких частях:

1. <sum_block>...</sum_block> - кумулятивные суммаризации всего диалога
2. ## Чанк: - конспекты групп сообщений среднего уровня детализации
3. Последние сообщения - полный текст последней части диалога

Учитывай всю предоставленную информацию при формировании ответа, особенно последние сообщения."""
    parts.append(system_msg)
    
    # Кумулятивный контекст
    if context_parts.get("cumulative"):
        parts.append(f"# Кумулятивный контекст (история обсуждения):\n{context_parts['cumulative']}")
    
    # Суммаризации L1
    if context_parts.get("l1_summaries"):
        parts.append(f"# Конспекты недавних обсуждений:\n{context_parts['l1_summaries']}")
    
    # Сырой хвост
    if context_parts.get("raw_tail"):
        parts.append(f"# Последние сообщения (полный текст):\n{context_parts['raw_tail']}")
    
    return "\n\n".join(parts)


def validate_context_config(config: Dict[str, Any]) -> List[str]:
    """Валидирует конфигурацию контекста"""
    errors = []
    
    if not config.get("enabled", True):
        return errors  # Если контекст отключен, не валидируем
    
    raw_tail = config.get("raw_tail", {})
    l1_chunks = config.get("l1_chunks", {})
    summarization = config.get("summarization", {})
    
    # Проверка сырого хвоста
    if raw_tail.get("char_limit", 0) <= 0:
        errors.append("raw_tail.char_limit должен быть положительным числом")
    
    if raw_tail.get("min_interactions", 0) < 0:
        errors.append("raw_tail.min_interactions не может быть отрицательным")
    
    # Проверка чанков L1
    if l1_chunks.get("target_char_limit", 0) <= 0:
        errors.append("l1_chunks.target_char_limit должен быть положительным числом")
    
    if l1_chunks.get("compression_ratio", 0) <= 1:
        errors.append("l1_chunks.compression_ratio должен быть больше 1")
    
    # Проверка порогов суммаризации
    if summarization.get("l2_trigger_count", 0) <= 0:
        errors.append("summarization.l2_trigger_count должен быть положительным числом")
    
    return errors


def generate_chunk_id(text: str, salt: str = "") -> str:
    """Генерирует уникальный идентификатор для чанка"""
    content = text + salt + datetime.now().isoformat()
    return hashlib.md5(content.encode()).hexdigest()[:16]


def safe_truncate(text: str, max_chars: int, suffix: str = "...") -> str:
    """Безопасно обрезает текст, не разбивая слова"""
    if len(text) <= max_chars:
        return text
    
    # Пытаемся обрезать на границе предложения
    truncated = text[:max_chars]
    last_period = truncated.rfind('. ')
    last_question = truncated.rfind('? ')
    last_exclamation = truncated.rfind('! ')
    
    cut_point = max(last_period, last_question, last_exclamation)
    if cut_point > max_chars * 0.7:  # Если нашли разумную точку обрезки
        return truncated[:cut_point + 1] + suffix
    
    # Иначе обрезаем на границе слова
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:
        return truncated[:last_space] + suffix
    
    return truncated + suffix


def format_interaction_for_summary(interaction: SimpleInteraction) -> str:
    """Форматирует взаимодействие для суммаризации"""
    return f"Пользователь: {interaction.user_message}\nАссистент: {interaction.assistant_message}"


def extract_message_indices_from_interactions(interactions: List[SimpleInteraction]) -> List[int]:
    """Извлекает все индексы сообщений из списка взаимодействий"""
    indices = []
    for interaction in interactions:
        indices.extend(interaction.message_indices)
    return sorted(set(indices))