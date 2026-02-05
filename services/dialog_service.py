"""
Сервис для управления диалогами (рефакторинг)
"""

from .dialogs import DialogManager

class DialogService:
    """Сервис для управления диалогами (фасад)"""
    
    def __init__(self):
        from container import container
        config = container.get_config()
        self.manager = DialogManager(config)
    
    # Делегируем все методы менеджеру
    def __getattr__(self, name):
        return getattr(self.manager, name)

# Глобальный экземпляр (для обратной совместимости)
dialog_service = DialogService()