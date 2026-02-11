"""
CRUD операции с диалогами
"""
from typing import Dict, Optional, List, Any
from datetime import datetime
from models.dialog import Dialog
from models.enums import MessageRole
from .storage import DialogStorage


class DialogOperations:
    """Базовые операции с диалогами"""
    
    @staticmethod
    def create_dialog(dialogs: Dict[str, Dialog], next_dialog_id: int, 
                     name: Optional[str] = None, config: dict = None) -> str:
        """Создает новый диалог"""
        dialog_id = str(next_dialog_id)
        
        if not name:
            default_name = config.get("default_name", "Новый чат") if config else "Новый чат"
            name = f"{default_name} {dialog_id}"
        
        dialog = Dialog(
            id=dialog_id,
            name=name,
            history=[],
            created=datetime.now(),
            updated=datetime.now()
        )
        
        dialogs[dialog_id] = dialog
        return dialog_id
    
    @staticmethod
    def delete_dialog(dialog_id: str, dialogs: Dict[str, Dialog], 
                     current_dialog_id: str, keep_current: bool,
                     storage: DialogStorage) -> bool:
        """Удаляет диалог с логикой переключения"""
        if dialog_id not in dialogs:
            return False
        
        # Получаем объект диалога для удаления
        dialog = dialogs[dialog_id]
        
        # Удаляем папку с файлами диалога
        storage.delete_dialog_folder(dialog)
        
        # Удаляем из памяти
        del dialogs[dialog_id]
        
        return True
    
    @staticmethod
    def rename_dialog(dialog_id: str, new_name: str, 
                     dialogs: Dict[str, Dialog], storage: DialogStorage) -> bool:
        """Переименовывает диалог с валидацией"""
        if dialog_id not in dialogs:
            return False
        
        # Получаем конфигурацию
        from container import container
        config = container.get_config()
        
        # Безопасно извлекаем настройки именования
        chat_naming_config = config.get("chat_naming", {})
        
        # Значения по умолчанию, если секция отсутствует
        max_length = chat_naming_config.get("max_name_length", 50)
        min_length = chat_naming_config.get("min_name_length", 1)
        name_validation = chat_naming_config.get("name_validation", {})
        allow_whitespace_only = name_validation.get("allow_whitespace_only", True)
        
        # Очищаем и валидируем новое название
        new_name = new_name.strip()
        
        # Проверка минимальной длины
        if len(new_name) < min_length:
            return False
        
        # Проверка на пустое название (после strip)
        if not new_name:
            return False
        
        # Проверка на только пробелы (если запрещено)
        if not allow_whitespace_only and new_name.isspace():
            return False
        
        # Ограничение максимальной длины
        if len(new_name) > max_length:
            new_name = new_name[:max_length]
        
        # Сохраняем старое название на случай ошибки
        old_name = dialogs[dialog_id].name
        
        try:
            dialogs[dialog_id].rename(new_name)
            storage.save_dialog(dialogs[dialog_id])
            return True
        except Exception:
            # В случае ошибки восстанавливаем старое название
            try:
                dialogs[dialog_id].rename(old_name)
            except:
                pass
            return False
    
    @staticmethod
    def get_current_dialog(dialogs: Dict[str, Dialog], 
                          current_dialog_id: str) -> Optional[Dialog]:
        """Получает текущий диалог"""
        if current_dialog_id and current_dialog_id in dialogs:
            return dialogs[current_dialog_id]
        return None
    
    @staticmethod
    def add_message(dialog_id: str, role: MessageRole, content: str,
                   dialogs: Dict[str, Dialog], storage: DialogStorage) -> bool:
        """Добавляет сообщение в диалог"""
        if dialog_id in dialogs:
            dialogs[dialog_id].add_message(role, content)
            storage.save_dialog(dialogs[dialog_id])
            return True
        return False