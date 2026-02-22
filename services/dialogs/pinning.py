# services/dialogs/pinning.py
"""
Логика закрепления диалогов
"""
from typing import Dict
from models.dialog import Dialog
from .storage import DialogStorage


class DialogPinning:
    """Управление закреплением диалогов"""

    @staticmethod
    def pin_dialog(dialog_id: str, dialogs: Dict[str, Dialog],
                   storage: DialogStorage) -> bool:
        """
        Закрепляет диалог.
        Все закреплённые диалоги сдвигаются вниз (их pinned_position увеличивается),
        новый диалог получает позицию 0.
        """
        if dialog_id not in dialogs:
            return False

        dialog = dialogs[dialog_id]

        # Если уже закреплён – ничего не делаем
        if dialog.pinned:
            return True

        # Увеличиваем позиции всех существующих закреплённых диалогов
        for other in dialogs.values():
            if other.pinned and other.id != dialog_id:
                if other.pinned_position is None:
                    other.pinned_position = 0
                else:
                    other.pinned_position += 1
                # Сохраняем изменения каждого затронутого диалога
                storage.save_dialog(other)

        # Закрепляем текущий диалог на позиции 0
        dialog.pinned = True
        dialog.pinned_position = 0
        storage.save_dialog(dialog)

        return True

    @staticmethod
    def unpin_dialog(dialog_id: str, dialogs: Dict[str, Dialog],
                     storage: DialogStorage) -> bool:
        """
        Открепляет диалог.
        Все закреплённые диалоги с большей позицией сдвигаются вверх.
        """
        if dialog_id not in dialogs:
            return False

        dialog = dialogs[dialog_id]

        # Если и так не закреплён – ничего не делаем
        if not dialog.pinned:
            return True

        removed_position = dialog.pinned_position

        # Открепляем диалог
        dialog.pinned = False
        dialog.pinned_position = None
        storage.save_dialog(dialog)

        # Уменьшаем позиции всех закреплённых диалогов, которые были ниже
        for other in dialogs.values():
            if (other.pinned and other.pinned_position is not None and
                    other.pinned_position > removed_position):
                other.pinned_position -= 1
                storage.save_dialog(other)

        return True