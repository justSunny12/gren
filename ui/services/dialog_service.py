# /services/dialog_service.py
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from models.dialog import Dialog, Message
from models.enums import MessageRole

class DialogService:
    """Сервис для управления диалогами"""
    
    def __init__(self):
        # Ленивый импорт container
        from container import container
        self.config = container.get_config().dialogs
        self.dialogs: Dict[str, Dialog] = {}
        self.current_dialog_id: Optional[str] = None
        self.next_dialog_id = 1
        
        # Создаем директорию для сохранения диалогов
        os.makedirs(self.config.save_dir, exist_ok=True)
        self.load_dialogs()
    
    def create_dialog(self, name: Optional[str] = None) -> str:
        """Создает новый диалог"""
        dialog_id = str(self.next_dialog_id)
        self.next_dialog_id += 1
        
        if not name:
            name = f"{self.config.default_name} {dialog_id}"
        
        dialog = Dialog(
            id=dialog_id,
            name=name,
            history=[],
            created=datetime.now(),
            updated=datetime.now()
        )
        
        self.dialogs[dialog_id] = dialog
        self.current_dialog_id = dialog_id
        self._save_dialog(dialog)  # Тихое сохранение
        
        return dialog_id
    
    def switch_dialog(self, dialog_id: str) -> bool:
        """Переключается на указанный диалог"""
        if dialog_id in self.dialogs:
            self.current_dialog_id = dialog_id
            return True
        return False
    
    def delete_dialog(self, dialog_id: str) -> bool:
        """Удаляет диалог"""
        if dialog_id in self.dialogs:
            # Удаляем файл с диалогом
            dialog_file = os.path.join(self.config.save_dir, f"dialog_{dialog_id}.json")
            if os.path.exists(dialog_file):
                os.remove(dialog_file)
            
            # Удаляем из памяти
            del self.dialogs[dialog_id]
            
            # Если удалили текущий диалог, переключаемся на другой
            if self.current_dialog_id == dialog_id:
                if self.dialogs:
                    self.current_dialog_id = list(self.dialogs.keys())[0]
                else:
                    self.current_dialog_id = None
            
            self._save_all_silent()  # Тихое сохранение
            return True
        return False
    
    def rename_dialog(self, dialog_id: str, new_name: str) -> bool:
        """Переименовывает диалог"""
        if dialog_id in self.dialogs:
            self.dialogs[dialog_id].rename(new_name)
            self._save_dialog(self.dialogs[dialog_id])  # Тихое сохранение
            return True
        return False
    
    def get_current_dialog(self) -> Optional[Dialog]:
        """Получает текущий активный диалог"""
        if self.current_dialog_id and self.current_dialog_id in self.dialogs:
            return self.dialogs[self.current_dialog_id]
        return None
    
    def get_dialog(self, dialog_id: str) -> Optional[Dialog]:
        """Получает диалог по ID"""
        return self.dialogs.get(dialog_id)
    
    def get_dialog_list(self) -> List[Dict[str, Any]]:
        """Получает список всех диалогов"""
        dialogs_list = []
        for dialog_id, dialog in self.dialogs.items():
            dialogs_list.append({
                "id": dialog_id,
                "name": dialog.name,
                "history_length": len(dialog.history),
                "created": dialog.created.isoformat(),
                "updated": dialog.updated.isoformat(),
                "is_current": (dialog_id == self.current_dialog_id)
            })
        
        # Сортируем по дате обновления (свежие сверху)
        dialogs_list.sort(key=lambda x: x["updated"], reverse=True)
        return dialogs_list
    
    def add_message(self, dialog_id: str, role: MessageRole, content: str) -> bool:
        """Добавляет сообщение в диалог"""
        if dialog_id in self.dialogs:
            self.dialogs[dialog_id].add_message(role, content)
            self._save_dialog(self.dialogs[dialog_id])  # Тихое сохранение
            return True
        return False
    
    def clear_dialog(self, dialog_id: str) -> bool:
        """Очищает историю диалога"""
        if dialog_id in self.dialogs:
            self.dialogs[dialog_id].clear_history()
            self._save_dialog(self.dialogs[dialog_id])  # Тихое сохранение
            return True
        return False
    
    def _save_dialog(self, dialog: Dialog):
        """Тихое сохранение диалога в файл"""
        try:
            dialog_file = os.path.join(self.config.save_dir, f"dialog_{dialog.id}.json")
            
            # Используем json_serialize вместо dict()
            if hasattr(dialog, 'json_serialize'):
                dialog_data = dialog.json_serialize()
            else:
                # Fallback: используем dict()
                dialog_data = dialog.dict()
                # Вручную конвертируем datetime в строки
                dialog_data["created"] = dialog.created.isoformat()
                dialog_data["updated"] = dialog.updated.isoformat()
                dialog_data["history"] = [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in dialog.history
                ]
            
            with open(dialog_file, 'w', encoding='utf-8') as f:
                json.dump(dialog_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            # Только при реальной ошибке
            print(f"❌ Ошибка при сохранении диалога {dialog.id}: {e}")
    
    def _save_all_silent(self):
        """Тихое сохранение всех диалогов"""
        for dialog_id, dialog in self.dialogs.items():
            self._save_dialog(dialog)
    
    def load_dialogs(self):
        """Загружает сохраненные диалоги с минимальным логированием"""
        try:
            if not os.path.exists(self.config.save_dir):
                os.makedirs(self.config.save_dir, exist_ok=True)
                return
            
            dialog_files = []
            for f in os.listdir(self.config.save_dir):
                if f.startswith("dialog_") and f.endswith(".json"):
                    file_path = os.path.join(self.config.save_dir, f)
                    
                    # Проверяем, не пустой ли файл
                    if os.path.getsize(file_path) == 0:
                        os.remove(file_path)
                        continue
                    
                    dialog_files.append(file_path)
            
            if dialog_files:
                print(f"📂 Загружено {len(dialog_files)} диалогов")
            
            for file_path in dialog_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read().strip()
                        
                        if not file_content:
                            os.remove(file_path)
                            continue
                        
                        # Загружаем JSON
                        dialog_data = json.loads(file_content)
                
                    # Конвертируем строки datetime обратно в datetime объекты
                    dialog_data["created"] = datetime.fromisoformat(dialog_data["created"])
                    dialog_data["updated"] = datetime.fromisoformat(dialog_data["updated"])
                    
                    # Конвертируем историю сообщений
                    messages = []
                    for msg_data in dialog_data.get("history", []):
                        # Конвертируем строку timestamp в datetime
                        msg_data["timestamp"] = datetime.fromisoformat(msg_data["timestamp"])
                        # Конвертируем строку role в enum
                        msg_data["role"] = MessageRole(msg_data["role"])
                        messages.append(Message(**msg_data))
                    dialog_data["history"] = messages
                    
                    # Создаем объект Dialog
                    dialog = Dialog(**dialog_data)
                    dialog_id = dialog.id
                    self.dialogs[dialog_id] = dialog
                    
                    # Обновляем next_dialog_id
                    dialog_num = int(dialog_id)
                    if dialog_num >= self.next_dialog_id:
                        self.next_dialog_id = dialog_num + 1
                    
                except json.JSONDecodeError:
                    # Тихо удаляем поврежденный файл
                    os.remove(file_path)
                except Exception:
                    # Тихо игнорируем другие ошибки
                    pass
            
            # Устанавливаем текущий диалог как последний обновленный
            if self.dialogs:
                dialogs_list = self.get_dialog_list()
                self.current_dialog_id = dialogs_list[0]["id"]
                
        except Exception:
            # Тихо игнорируем общие ошибки
            pass

# Глобальный экземпляр
dialog_service = DialogService()