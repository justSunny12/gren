# services/context/interaction.py
from dataclasses import dataclass
from typing import List

@dataclass
class SimpleInteraction:
    """Упрощённое представление взаимодействия пользователь-ассистент."""
    user_message: str
    assistant_message: str
    message_indices: List[int] = None

    def __post_init__(self):
        if self.message_indices is None:
            self.message_indices = []

    @property
    def text(self) -> str:
        return f"Пользователь: {self.user_message}\nАссистент: {self.assistant_message}"

    @property
    def char_count(self) -> int:
        return len(self.text)