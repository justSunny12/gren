# services/dialogs/storage.py
"""
Работа с файловой системой (загрузка/сохранение диалогов) с новой структурой
"""
import os
import json
import shutil
from datetime import datetime
from typing import Dict, Optional
from models.dialog import Dialog
from models.enums import MessageRole
from models.message import Message
from container import container


class DialogStorage:
    """Управление сохранением и загрузкой диалогов с новой структурой файлов"""
    
    def __init__(self, config: dict):
        self.save_dir = config.get("save_dir", "saved_dialogs")
        os.makedirs(self.save_dir, exist_ok=True)
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger
    
    def _get_chat_folder_name(self, dialog: Dialog) -> str:
        """Генерирует имя папки для диалога: chat_YYYYMMDDTHHMMSS-fff"""
        datetime_str = dialog.created.strftime("%Y%m%dT%H%M%S")
        microseconds = dialog.created.strftime("%f")[:3]
        return f"chat_{datetime_str}-{microseconds}"
    
    def _get_history_file_name(self, dialog: Dialog) -> str:
        """Генерирует имя файла истории: history_YYYYMMDDTHHMMSS-fff.json"""
        datetime_str = dialog.created.strftime("%Y%m%dT%H%M%S")
        microseconds = dialog.created.strftime("%f")[:3]
        return f"history_{datetime_str}-{microseconds}.json"
    
    def _get_chat_folder_path(self, dialog: Dialog) -> str:
        folder_name = self._get_chat_folder_name(dialog)
        return os.path.join(self.save_dir, folder_name)
    
    def _get_history_file_path(self, dialog: Dialog) -> str:
        folder_path = self._get_chat_folder_path(dialog)
        file_name = self._get_history_file_name(dialog)
        return os.path.join(folder_path, file_name)
    
    def save_dialog(self, dialog: Dialog) -> bool:
        """Сохраняет диалог в файл истории (тихо)"""
        try:
            folder_path = self._get_chat_folder_path(dialog)
            os.makedirs(folder_path, exist_ok=True)
            
            history_file = self._get_history_file_path(dialog)
            dialog_data = dialog.to_dict()  # ранее было dialog.json_serialize()
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(dialog_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.warning("Ошибка сохранения диалога %s: %s", dialog.id, e)
            return False
    
    def load_dialogs(self) -> Dict[str, Dialog]:
        """Загружает все диалоги из файлов с новой структурой"""
        dialogs = {}
        
        try:
            if not os.path.exists(self.save_dir):
                self.logger.info("Директория сохраненных диалогов не существует: %s", self.save_dir)
                return dialogs
            
            for folder_name in os.listdir(self.save_dir):
                folder_path = os.path.join(self.save_dir, folder_name)
                
                if not os.path.isdir(folder_path) or not folder_name.startswith('chat_'):
                    continue
                
                for filename in os.listdir(folder_path):
                    if filename.startswith("history_") and filename.endswith(".json"):
                        history_file = os.path.join(folder_path, filename)
                        
                        if os.path.getsize(history_file) == 0:
                            self.logger.warning("Пустой файл истории: %s", history_file)
                            os.remove(history_file)
                            continue
                        
                        try:
                            with open(history_file, 'r', encoding='utf-8') as f:
                                dialog_data = json.load(f)
                            
                            dialog_data["created"] = datetime.fromisoformat(dialog_data["created"])
                            dialog_data["updated"] = datetime.fromisoformat(dialog_data["updated"])
                            
                            messages = []
                            for msg_data in dialog_data.get("history", []):
                                msg_data["timestamp"] = datetime.fromisoformat(msg_data["timestamp"])
                                msg_data["role"] = MessageRole(msg_data["role"])
                                messages.append(Message(**msg_data))
                            dialog_data["history"] = messages
                            
                            dialog_data["pinned"] = dialog_data.get("pinned", False)
                            dialog_data["pinned_position"] = dialog_data.get("pinned_position")
                            
                            dialog = Dialog(**dialog_data)
                            dialogs[dialog.id] = dialog
                            
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            self.logger.error("Ошибка загрузки файла истории %s: %s", history_file, e)
                            continue
                
        except Exception as e:
            self.logger.error("Критическая ошибка при загрузке диалогов: %s", e)
        
        return dialogs
    
    def delete_dialog_folder(self, dialog: Dialog) -> bool:
        """Удаляет папку диалога и все её содержимое"""
        try:
            folder_path = self._get_chat_folder_path(dialog)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                return True
            return False
        except Exception as e:
            self.logger.warning("Ошибка удаления папки диалога %s: %s", dialog.id, e)
            return False