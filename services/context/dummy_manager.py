# services/context/dummy_manager.py
"""
Заглушка для менеджера контекста, когда контекст отключен
"""
from typing import Dict, Any
from models.dialog import Dialog


class DummyContextManager:
    """Заглушка для работы без контекста"""
    
    def __init__(self, dialog: Dialog, config: Dict[str, Any]):
        self.dialog = dialog
        self.config = config
    
    def get_context_for_generation(self) -> str:
        """Возвращает пустой контекст"""
        return ""
    
    def add_interaction_to_context(self, user_message: str, assistant_message: str):
        """Пустой метод"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает пустую статистику"""
        return {"enabled": False}
    
    def save_context_state(self):
        """Пустой метод"""
        pass
    
    def cleanup(self):
        """Пустой метод"""
        pass