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
        """Закрепляет диалог"""
        if dialog_id not in dialogs:
            return False
        
        dialog = dialogs[dialog_id]
        
        if dialog.pinned:
            return True
        
        # Сдвигаем все закрепленные вниз
        for other_dialog in dialogs.values():
            if other_dialog.pinned and other_dialog.id != dialog_id:
                if other_dialog.pinned_position is None:
                    other_dialog.pinned_position = 0
                other_dialog.pinned_position += 1
                storage.save_dialog(other_dialog)
        
        # Закрепляем текущий
        dialog.pinned = True
        dialog.pinned_position = 0
        storage.save_dialog(dialog)
        
        return True
    
    @staticmethod
    def unpin_dialog(dialog_id: str, dialogs: Dict[str, Dialog],
                    storage: DialogStorage) -> bool:
        """Открепляет диалог"""
        if dialog_id not in dialogs:
            return False
        
        dialog = dialogs[dialog_id]
        
        if not dialog.pinned:
            return True
        
        unpinned_position = dialog.pinned_position
        
        # Открепляем
        dialog.pinned = False
        dialog.pinned_position = None
        storage.save_dialog(dialog)
        
        # Сдвигаем чаты ниже вверх
        for other_dialog in dialogs.values():
            if (other_dialog.pinned and 
                other_dialog.pinned_position is not None and 
                other_dialog.pinned_position > unpinned_position):
                other_dialog.pinned_position -= 1
                storage.save_dialog(other_dialog)
        
        return True