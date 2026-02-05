"""
Работа с файловой системой (загрузка/сохранение диалогов)
"""
import os
import json
from datetime import datetime
from typing import Dict, Optional
from models.dialog import Dialog
from models.enums import MessageRole
from models.message import Message


class DialogStorage:
    """Управление сохранением и загрузкой диалогов"""
    
    def __init__(self, config: dict):
        self.save_dir = config.get("save_dir", "saved_dialogs")
        os.makedirs(self.save_dir, exist_ok=True)
    
    def save_dialog(self, dialog: Dialog) -> bool:
        """Сохраняет диалог в файл (тихо)"""
        try:
            dialog_file = os.path.join(self.save_dir, f"dialog_{dialog.id}.json")
            dialog_data = dialog.json_serialize()
            
            with open(dialog_file, 'w', encoding='utf-8') as f:
                json.dump(dialog_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def delete_dialog_file(self, dialog_id: str) -> bool:
        """Удаляет файл диалога (тихо)"""
        try:
            dialog_file = os.path.join(self.save_dir, f"dialog_{dialog_id}.json")
            if os.path.exists(dialog_file):
                os.remove(dialog_file)
            return True
        except Exception:
            return False
    
    def load_dialogs(self) -> Dict[str, Dialog]:
        """Загружает все диалоги из файлов (тихо)"""
        dialogs = {}
        
        try:
            if not os.path.exists(self.save_dir):
                return dialogs
            
            for filename in os.listdir(self.save_dir):
                if not (filename.startswith("dialog_") and filename.endswith(".json")):
                    continue
                
                file_path = os.path.join(self.save_dir, filename)
                
                if os.path.getsize(file_path) == 0:
                    os.remove(file_path)
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        dialog_data = json.load(f)
                    
                    # Восстанавливаем даты
                    dialog_data["created"] = datetime.fromisoformat(dialog_data["created"])
                    dialog_data["updated"] = datetime.fromisoformat(dialog_data["updated"])
                    
                    # Восстанавливаем сообщения
                    messages = []
                    for msg_data in dialog_data.get("history", []):
                        msg_data["timestamp"] = datetime.fromisoformat(msg_data["timestamp"])
                        msg_data["role"] = MessageRole(msg_data["role"])
                        messages.append(Message(**msg_data))
                    dialog_data["history"] = messages
                    
                    # Новые поля для закрепления
                    dialog_data["pinned"] = dialog_data.get("pinned", False)
                    dialog_data["pinned_position"] = dialog_data.get("pinned_position")
                    
                    dialog = Dialog(**dialog_data)
                    dialogs[dialog.id] = dialog
                    
                except (json.JSONDecodeError, KeyError):
                    # Поврежденный файл - удаляем
                    os.remove(file_path)
                
        except Exception:
            pass
        
        return dialogs
    
    def save_all(self, dialogs: Dict[str, Dialog]) -> bool:
        """Сохраняет все диалоги (тихо)"""
        try:
            for dialog in dialogs.values():
                self.save_dialog(dialog)
            return True
        except Exception:
            return False