# handlers/__init__.py
from .mediator import ui_handlers, UIMediator

# Глобальный экземпляр для обратной совместимости (теперь это ссылка на существующий)
ui_handlers = ui_handlers
__all__ = ['ui_handlers', 'UIMediator']