# /classes/dialog_manager.py
import json
import os
from datetime import datetime

class DialogManager:
    """Менеджер для управления диалогами/чатами"""
    
    def __init__(self):
        self.dialogs = {}  # {dialog_id: {"name": str, "history": list, "created": timestamp}}
        self.current_dialog_id = None
        self.next_dialog_id = 1
        
        # Создаем директорию для сохранения диалогов
        self.save_dir = "saved_dialogs"
        os.makedirs(self.save_dir, exist_ok=True)
        self.load_dialogs()
    
    def create_new_dialog(self, name=None):
        """Создает новый диалог"""
        dialog_id = str(self.next_dialog_id)
        self.next_dialog_id += 1
        
        if not name:
            name = f"Чат {dialog_id}"
        
        self.dialogs[dialog_id] = {
            "id": dialog_id,
            "name": name,
            "history": [],
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat()
        }
        
        self.current_dialog_id = dialog_id
        self.save_dialogs()
        return dialog_id
    
    def switch_dialog(self, dialog_id):
        """Переключается на указанный диалог"""
        if dialog_id in self.dialogs:
            self.current_dialog_id = dialog_id
            return True
        return False
    
    def delete_dialog(self, dialog_id):
        """Удаляет диалог"""
        if dialog_id in self.dialogs:
            # Удаляем файл с диалогом
            dialog_file = os.path.join(self.save_dir, f"dialog_{dialog_id}.json")
            if os.path.exists(dialog_file):
                os.remove(dialog_file)
            
            del self.dialogs[dialog_id]
            
            # Если удалили текущий диалог, переключаемся на другой
            if self.current_dialog_id == dialog_id:
                if self.dialogs:
                    self.current_dialog_id = list(self.dialogs.keys())[0]
                else:
                    self.current_dialog_id = None
            
            self.save_dialogs()
            return True
        return False
    
    def rename_dialog(self, dialog_id, new_name):
        """Переименовывает диалог"""
        if dialog_id in self.dialogs:
            self.dialogs[dialog_id]["name"] = new_name
            self.dialogs[dialog_id]["updated"] = datetime.now().isoformat()
            self.save_dialogs()
            return True
        return False
    
    def get_current_dialog(self):
        """Получает текущий активный диалог"""
        if self.current_dialog_id and self.current_dialog_id in self.dialogs:
            return self.dialogs[self.current_dialog_id]
        return None
    
    def get_dialog_list(self):
        """Получает список всех диалогов"""
        dialogs_list = []
        for dialog_id, dialog_info in self.dialogs.items():
            dialogs_list.append({
                "id": dialog_id,
                "name": dialog_info["name"],
                "history_length": len(dialog_info["history"]),
                "created": dialog_info["created"],
                "updated": dialog_info["updated"],
                "is_current": (dialog_id == self.current_dialog_id)
            })
        
        # Сортируем по дате обновления (свежие сверху)
        dialogs_list.sort(key=lambda x: x["updated"], reverse=True)
        return dialogs_list
    
    def add_message(self, dialog_id, role, content):
        """Добавляет сообщение в диалог"""
        if dialog_id in self.dialogs:
            self.dialogs[dialog_id]["history"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            self.dialogs[dialog_id]["updated"] = datetime.now().isoformat()
            self.save_dialogs()
    
    def clear_dialog(self, dialog_id):
        """Очищает историю диалога"""
        if dialog_id in self.dialogs:
            self.dialogs[dialog_id]["history"] = []
            self.dialogs[dialog_id]["updated"] = datetime.now().isoformat()
            self.save_dialogs()
    
    def save_dialogs(self):
        """Сохраняет все диалоги в файлы"""
        for dialog_id, dialog_info in self.dialogs.items():
            dialog_file = os.path.join(self.save_dir, f"dialog_{dialog_id}.json")
            with open(dialog_file, 'w', encoding='utf-8') as f:
                json.dump(dialog_info, f, ensure_ascii=False, indent=2)
    
    def load_dialogs(self):
        """Загружает сохраненные диалоги"""
        try:
            dialog_files = [f for f in os.listdir(self.save_dir) if f.startswith("dialog_") and f.endswith(".json")]
            
            for dialog_file in dialog_files:
                file_path = os.path.join(self.save_dir, dialog_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    dialog_info = json.load(f)
                
                dialog_id = dialog_info["id"]
                self.dialogs[dialog_id] = dialog_info
                
                # Обновляем next_dialog_id
                dialog_num = int(dialog_id)
                if dialog_num >= self.next_dialog_id:
                    self.next_dialog_id = dialog_num + 1
            
            # Устанавливаем текущий диалог как последний обновленный
            if self.dialogs:
                dialogs_list = self.get_dialog_list()
                self.current_dialog_id = dialogs_list[0]["id"]
                
        except Exception as e:
            print(f"Ошибка при загрузке диалогов: {e}")