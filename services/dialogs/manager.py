"""
Основной менеджер диалогов (координация всех подсистем)
Заменяет старый dialog_service.py
"""
from typing import Dict, Optional, List, Any
from datetime import datetime
from models.dialog import Dialog
from models.enums import MessageRole
from .storage import DialogStorage
from .operations import DialogOperations
from .pinning import DialogPinning
from .grouper import DialogGrouper


class DialogManager:
    """Главный координатор для работы с диалогами (замена DialogService)"""
    
    def __init__(self, config: dict = None):
        # Получаем конфиг лениво, чтобы избежать циклических импортов
        if config is None:
            from container import container
            config = container.get_config()
        
        self.config = config.get("dialogs", {})
        self.storage = DialogStorage(config)
        self.operations = DialogOperations()
        self.pinning = DialogPinning()
        self.grouper = DialogGrouper()
        
        self.dialogs: Dict[str, Dialog] = {}
        self.current_dialog_id: Optional[str] = None
        self.next_dialog_id = 1
        
        # Инициализация
        self._init_dialogs()
    
    def _init_dialogs(self):
        """Инициализация диалогов из хранилища"""
        self.dialogs = self.storage.load_dialogs()
        
        if self.dialogs:
            # Обновляем счетчик ID
            max_id = max((int(did) for did in self.dialogs.keys()), default=0)
            self.next_dialog_id = max_id + 1
            
            # Устанавливаем текущий диалог (первый в отсортированном списке)
            dialogs_list = self.get_dialog_list()
            self.current_dialog_id = dialogs_list[0]["id"] if dialogs_list else None
    
    # ========== ДЕЛЕГИРУЮЩИЕ МЕТОДЫ ==========
    
    def create_dialog(self, name: Optional[str] = None) -> str:
        dialog_id = self.operations.create_dialog(
            dialogs=self.dialogs,
            next_dialog_id=self.next_dialog_id,
            name=name,
            config=self.config
        )
        
        if dialog_id:
            self.next_dialog_id += 1
            self.current_dialog_id = dialog_id
            self.storage.save_dialog(self.dialogs[dialog_id])
        
        return dialog_id
    
    def save_dialog(self, dialog_id: str) -> bool:
        """Сохраняет диалог по ID"""
        if dialog_id in self.dialogs:
            return self.storage.save_dialog(self.dialogs[dialog_id])
        return False
    
    def switch_dialog(self, dialog_id: str) -> bool:
        if dialog_id in self.dialogs:
            self.current_dialog_id = dialog_id
            return True
        return False
    
    def delete_dialog(self, dialog_id: str, keep_current: bool = True) -> bool:
        result = self.operations.delete_dialog(
            dialog_id=dialog_id,
            dialogs=self.dialogs,
            current_dialog_id=self.current_dialog_id,
            keep_current=keep_current,
            storage=self.storage
        )
        
        if result and self.current_dialog_id == dialog_id:
            # Если удалили текущий, выбираем новый
            if self.dialogs:
                self.current_dialog_id = list(self.dialogs.keys())[0]
            else:
                self.current_dialog_id = None
        
        return result
    
    def pin_dialog(self, dialog_id: str) -> bool:
        return self.pinning.pin_dialog(
            dialog_id=dialog_id,
            dialogs=self.dialogs,
            storage=self.storage
        )
    
    def unpin_dialog(self, dialog_id: str) -> bool:
        return self.pinning.unpin_dialog(
            dialog_id=dialog_id,
            dialogs=self.dialogs,
            storage=self.storage
        )
    
    def rename_dialog(self, dialog_id: str, new_name: str) -> bool:
        return self.operations.rename_dialog(
            dialog_id=dialog_id,
            new_name=new_name,
            dialogs=self.dialogs,
            storage=self.storage
        )
    
    def get_current_dialog(self) -> Optional[Dialog]:
        return self.operations.get_current_dialog(
            dialogs=self.dialogs,
            current_dialog_id=self.current_dialog_id
        )
    
    def get_dialog(self, dialog_id: str) -> Optional[Dialog]:
        return self.dialogs.get(dialog_id)
    
    def get_dialog_list(self) -> List[Dict[str, Any]]:
        return self.grouper.get_dialog_list(
            dialogs=self.dialogs,
            current_dialog_id=self.current_dialog_id
        )
    
    def get_dialog_list_with_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.grouper.get_dialog_list_with_groups(
            dialogs=self.dialogs,
            current_dialog_id=self.current_dialog_id
        )
    
    def update_dialog_timestamp(self, dialog_id: str) -> bool:
        return self.operations.update_dialog_timestamp(
            dialog_id=dialog_id,
            dialogs=self.dialogs,
            storage=self.storage
        )
    
    def add_message(self, dialog_id: str, role: MessageRole, content: str) -> bool:
        return self.operations.add_message(
            dialog_id=dialog_id,
            role=role,
            content=content,
            dialogs=self.dialogs,
            storage=self.storage
        )
    
    def clear_dialog(self, dialog_id: str) -> bool:
        return self.operations.clear_dialog(
            dialog_id=dialog_id,
            dialogs=self.dialogs,
            storage=self.storage
        )