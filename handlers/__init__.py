# handlers/__init__.py
from .mediator import ui_handlers, UIMediator

# Глобальный экземпляр для обратной совместимости (теперь это ссылка на существующий)
__all__ = ['ui_handlers', 'UIMediator']