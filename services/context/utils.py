# services/context/utils.py (исправленная версия)
"""
Утилиты для работы с контекстом
"""
import re
from typing import List

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
                # print(f"✅ Разрешено переполнение чанка: "
                #       f"{interaction_size} > {target_chars} символов "
                #       f"(одно большое взаимодействие)")
                continue
            else:
                # Если чанк не пустой, сохраняем его и начинаем новый
                chunks.append(current_chunk.copy())
                current_chunk = [interaction]
                current_size = interaction_size
                # print(f"✅ Создан переполненный чанк: "
                #       f"{interaction_size} символов")
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

def format_interaction_for_summary(interaction: SimpleInteraction) -> str:
    """Форматирует взаимодействие для суммаризации"""
    return f"Пользователь: {interaction.user_message}\nАссистент: {interaction.assistant_message}"


def extract_message_indices_from_interactions(interactions: List[SimpleInteraction]) -> List[int]:
    """Извлекает все индексы сообщений из списка взаимодействий"""
    indices = []
    for interaction in interactions:
        indices.extend(interaction.message_indices)
    return sorted(set(indices))