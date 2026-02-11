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


class DialogStorage:
    """Управление сохранением и загрузкой диалогов с новой структурой файлов"""
    
    def __init__(self, config: dict):
        self.save_dir = config.get("save_dir", "saved_dialogs")
        os.makedirs(self.save_dir, exist_ok=True)
    
    def _get_chat_folder_name(self, dialog: Dialog) -> str:
        """Генерирует имя папки для диалога: chat_YYYYMMDDTHHMMSS-fff"""
        # Формат: ГодМесяцДеньTЧасМинутаСекунда-Микросекунды(первые 3 цифры)
        datetime_str = dialog.created.strftime("%Y%m%dT%H%M%S")
        microseconds = dialog.created.strftime("%f")[:3]  # Берем только первые 3 цифры
        return f"chat_{datetime_str}-{microseconds}"
    
    def _get_history_file_name(self, dialog: Dialog) -> str:
        """Генерирует имя файла истории: history_YYYYMMDDTHHMMSS-fff.json"""
        datetime_str = dialog.created.strftime("%Y%m%dT%H%M%S")
        microseconds = dialog.created.strftime("%f")[:3]  # Берем только первые 3 цифры
        return f"history_{datetime_str}-{microseconds}.json"
    
    def _get_chat_folder_path(self, dialog: Dialog) -> str:
        """Возвращает полный путь к папке диалога"""
        folder_name = self._get_chat_folder_name(dialog)
        return os.path.join(self.save_dir, folder_name)
    
    def _get_history_file_path(self, dialog: Dialog) -> str:
        """Возвращает полный путь к файлу истории диалога"""
        folder_path = self._get_chat_folder_path(dialog)
        file_name = self._get_history_file_name(dialog)
        return os.path.join(folder_path, file_name)
    
    def save_dialog(self, dialog: Dialog) -> bool:
        """Сохраняет диалог в файл истории (тихо)"""
        try:
            # Создаем папку для диалога
            folder_path = self._get_chat_folder_path(dialog)
            os.makedirs(folder_path, exist_ok=True)
            
            # Сохраняем историю
            history_file = self._get_history_file_path(dialog)
            dialog_data = dialog.json_serialize()
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(dialog_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Сохранена история диалога: {os.path.basename(history_file)}")
            return True
            
        except Exception as e:
            print(f"⚠️ Ошибка сохранения диалога {dialog.id}: {e}")
            return False
    
    def load_dialogs(self) -> Dict[str, Dialog]:
        """Загружает все диалоги из файлов с новой структурой"""
        dialogs = {}
        
        try:
            if not os.path.exists(self.save_dir):
                print(f"ℹ️ Директория сохраненных диалогов не существует: {self.save_dir}")
                return dialogs
            
            # Ищем папки, начинающиеся с 'chat_'
            for folder_name in os.listdir(self.save_dir):
                folder_path = os.path.join(self.save_dir, folder_name)
                
                # Проверяем, что это папка и имя соответствует шаблону
                if not os.path.isdir(folder_path) or not folder_name.startswith('chat_'):
                    continue
                
                # Ищем файл истории в папке
                for filename in os.listdir(folder_path):
                    if filename.startswith("history_") and filename.endswith(".json"):
                        history_file = os.path.join(folder_path, filename)
                        
                        if os.path.getsize(history_file) == 0:
                            print(f"⚠️ Пустой файл истории: {history_file}")
                            os.remove(history_file)
                            continue
                        
                        try:
                            with open(history_file, 'r', encoding='utf-8') as f:
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
                            
                            print(f"📂 Загружен диалог из: {folder_name}/{filename}")
                            
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            print(f"❌ Ошибка загрузки файла истории {history_file}: {e}")
                            # Поврежденный файл - пропускаем
                            continue
                
        except Exception as e:
            print(f"❌ Критическая ошибка при загрузке диалогов: {e}")
        
        return dialogs
    
    def delete_dialog_folder(self, dialog: Dialog) -> bool:
        """Удаляет папку диалога и все её содержимое"""
        try:
            folder_path = self._get_chat_folder_path(dialog)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                print(f"🗑️ Удалена папка диалога: {os.path.basename(folder_path)}")
                return True
            return False
        except Exception as e:
            print(f"⚠️ Ошибка удаления папки диалога {dialog.id}: {e}")
            return False