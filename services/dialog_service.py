# /services/dialog_service.py
import json
import os
from datetime import datetime, timedelta, date
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
        self._save_dialog(dialog)
        
        return dialog_id
    
    def switch_dialog(self, dialog_id: str) -> bool:
        """Переключается на указанный диалог"""
        if dialog_id in self.dialogs:
            self.current_dialog_id = dialog_id
            return True
        return False
    
    def delete_dialog(self, dialog_id: str, keep_current: bool = True) -> bool:
        """
        Удаляет диалог с возможностью сохранить текущий активный чат
        
        :param dialog_id: ID диалога для удаления
        :param keep_current: Если True - не менять текущий активный чат при удалении НЕактивного
                           Если False - всегда переключаться по стандартной логике
        :return: True если успешно
        """
        if dialog_id not in self.dialogs:
            return False
        
        # Определяем, удаляем ли мы текущий активный чат
        is_current = (self.current_dialog_id == dialog_id)
        
        # Если удаляем НЕактивный чат и хотим сохранить текущий
        if not is_current and keep_current:
            # Просто удаляем чат, не меняя текущий
            dialog_file = os.path.join(self.config.save_dir, f"dialog_{dialog_id}.json")
            if os.path.exists(dialog_file):
                os.remove(dialog_file)
            
            del self.dialogs[dialog_id]
            self._save_all_silent()
            return True
        
        # Получаем список диалогов ДО удаления (уже отсортирован по updated)
        dialogs_before = self.get_dialog_list()
        current_index = -1
        for i, d in enumerate(dialogs_before):
            if d['id'] == dialog_id:
                current_index = i
                break
        
        # Удаляем файл
        dialog_file = os.path.join(self.config.save_dir, f"dialog_{dialog_id}.json")
        if os.path.exists(dialog_file):
            os.remove(dialog_file)
        
        # Удаляем из памяти
        del self.dialogs[dialog_id]
        
        # Определяем следующий чат для переключения (только если удаляем активный)
        new_dialog_id = None
        
        # Логика переключения ТОЛЬКО если is_current=True или keep_current=False
        if is_current or not keep_current:
            # Ищем чат для переключения
            if current_index >= 0:
                # 1. Сначала пробуем взять чат ВЫШЕ (предыдущий в списке)
                if current_index > 0:
                    prev_dialog = dialogs_before[current_index - 1]
                    if prev_dialog['id'] != dialog_id and prev_dialog['id'] in self.dialogs:
                        new_dialog_id = prev_dialog['id']
                
                # 2. Если выше нет, пробуем НИЖЕ (следующий в списке)
                if not new_dialog_id and current_index + 1 < len(dialogs_before):
                    next_dialog = dialogs_before[current_index + 1]
                    if next_dialog['id'] != dialog_id and next_dialog['id'] in self.dialogs:
                        new_dialog_id = next_dialog['id']
            
            # 3. Если все еще не нашли, берем первый доступный
            if not new_dialog_id and self.dialogs:
                new_dialog_id = list(self.dialogs.keys())[0]
            
            # Обновляем текущий диалог
            if new_dialog_id and new_dialog_id in self.dialogs:
                self.current_dialog_id = new_dialog_id
            elif self.dialogs:
                # Если не указали конкретный, но есть диалоги - берем первый
                self.current_dialog_id = list(self.dialogs.keys())[0]
            else:
                self.current_dialog_id = None
        
        self._save_all_silent()
        return True
    
    def pin_dialog(self, dialog_id: str) -> bool:
        """Закрепляет диалог (ставит на первую позицию в закрепленных)"""
        if dialog_id not in self.dialogs:
            return False
        
        dialog = self.dialogs[dialog_id]
        
        # Если уже закреплен - ничего не делаем
        if dialog.pinned:
            return True
        
        # Сдвигаем все существующие закрепленные чаты вниз
        for other_id, other_dialog in self.dialogs.items():
            if other_dialog.pinned:
                if other_dialog.pinned_position is None:
                    other_dialog.pinned_position = 0
                other_dialog.pinned_position += 1
        
        # Закрепляем текущий чат на позиции 0
        dialog.pinned = True
        dialog.pinned_position = 0
        
        self._save_dialog(dialog)
        
        # Сохраняем сдвинутые чаты
        for other_id, other_dialog in self.dialogs.items():
            if other_dialog.pinned and other_id != dialog_id:
                self._save_dialog(other_dialog)
        
        return True
    
    def unpin_dialog(self, dialog_id: str) -> bool:
        """Открепляет диалог и перестраивает позиции"""
        if dialog_id not in self.dialogs:
            return False
        
        dialog = self.dialogs[dialog_id]
        
        # Если не закреплен - ничего не делаем
        if not dialog.pinned:
            return True
        
        # Запоминаем позицию открепляемого чата
        unpinned_position = dialog.pinned_position
        
        # Открепляем
        dialog.pinned = False
        dialog.pinned_position = None
        
        self._save_dialog(dialog)
        
        # Сдвигаем все чаты ниже открепленного вверх
        for other_id, other_dialog in self.dialogs.items():
            if (other_dialog.pinned and 
                other_dialog.pinned_position is not None and 
                other_dialog.pinned_position > unpinned_position):
                other_dialog.pinned_position -= 1
                self._save_dialog(other_dialog)
        
        return True
    
    def rename_dialog(self, dialog_id: str, new_name: str) -> bool:
        """Переименовывает диалог с валидацией"""
        if dialog_id not in self.dialogs:
            return False
        
        # Получаем конфигурацию
        from container import container
        config = container.get_config()
        
        # Очищаем и валидируем новое название
        new_name = new_name.strip()
        
        # Проверка минимальной длины
        if len(new_name) < config.chat_naming.min_name_length:
            return False
        
        # Проверка на пустое название (после trim)
        if not new_name:
            return False
        
        # Проверка на только пробелы
        if not config.chat_naming.name_validation.allow_whitespace_only and new_name.isspace():
            return False
        
        # Ограничение максимальной длины
        if len(new_name) > config.chat_naming.max_name_length:
            new_name = new_name[:config.chat_naming.max_name_length]
        
        # Сохраняем старое название на случай ошибки
        old_name = self.dialogs[dialog_id].name
        
        try:
            self.dialogs[dialog_id].rename(new_name)
            self._save_dialog(self.dialogs[dialog_id])
            return True
        except Exception:
            # В случае ошибки восстанавливаем старое название
            try:
                self.dialogs[dialog_id].rename(old_name)
            except:
                pass
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
        """Получает список всех диалогов с информацией о закреплении"""
        dialogs_list = []
        for dialog_id, dialog in self.dialogs.items():
            dialog_info = {
                "id": dialog_id,
                "name": dialog.name,
                "history_length": len(dialog.history),
                "created": dialog.created.isoformat(),
                "updated": dialog.updated.isoformat(),
                "is_current": (dialog_id == self.current_dialog_id),
                "pinned": dialog.pinned,  # ← Убедитесь что это есть
                "pinned_position": dialog.pinned_position  # ← Убедитесь что это есть
            }
            dialogs_list.append(dialog_info)
        
        # Сортируем: сначала закрепленные (по позиции), потом обычные
        dialogs_list.sort(key=lambda x: (
            -1 if x["pinned"] else 0,  # Закрепленные вверху
            x["pinned_position"] if x["pinned"] and x["pinned_position"] is not None else 999,  # Сортировка по позиции
            x["updated"]  # Обычные сортируем по updated
        ), reverse=True)
        
        return dialogs_list
    
    def get_dialog_list_with_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """Получает список всех диалогов с группировкой по датам и закрепленными"""
        dialogs_list = self.get_dialog_list()
        if not dialogs_list:
            return {}
        
        today_date = date.today()
        yesterday_date = today_date - timedelta(days=1)
        week_ago_date = today_date - timedelta(days=7)
        month_ago_date = today_date - timedelta(days=30)
        
        # Группируем диалоги - сначала отделяем закрепленные
        groups = {
            "pinned": [],  # НОВАЯ ГРУППА: Закрепленные
            "today": [],  # Сегодня
            "yesterday": [],  # Вчера  
            "week": [],  # Последние 7 дней (кроме сегодня и вчера)
            "month": [],  # Месяц (кроме последних 7 дней)
            "older": []  # Более месяца
        }
        
        for dialog_info in dialogs_list:
            # Если диалог закреплен - добавляем в группу "pinned"
            if dialog_info.get("pinned", False):
                groups["pinned"].append(dialog_info)
                continue  # ← Ключевое слово! Закрепленные не попадают в другие группы
            
            # Парсим дату последнего обновления
            try:
                last_update = datetime.fromisoformat(dialog_info["updated"].replace('Z', '+00:00'))
                last_update_date = last_update.date()
                
                # Определяем группу
                if last_update_date == today_date:
                    groups["today"].append(dialog_info)
                elif last_update_date == yesterday_date:
                    groups["yesterday"].append(dialog_info)
                elif week_ago_date <= last_update_date < yesterday_date:
                    groups["week"].append(dialog_info)
                elif month_ago_date <= last_update_date < week_ago_date:
                    groups["month"].append(dialog_info)
                else:
                    groups["older"].append(dialog_info)
                    
            except Exception:
                groups["older"].append(dialog_info)
        
        # Сортируем закрепленные по pinned_position (чем меньше, тем выше)
        if groups["pinned"]:
            groups["pinned"].sort(key=lambda x: x.get("pinned_position", 999))
        
        # Убираем пустые группы
        result = {}
        if groups["pinned"]:
            result["Закрепленные"] = groups["pinned"]
        if groups["today"]:
            result["Сегодня"] = groups["today"]
        if groups["yesterday"]:
            result["Вчера"] = groups["yesterday"]
        if groups["week"]:
            result["7 дней"] = groups["week"]
        if groups["month"]:
            result["Месяц"] = groups["month"]
        if groups["older"]:
            result["Более месяца"] = groups["older"]
        
        return result
    
    def update_dialog_timestamp(self, dialog_id: str):
        """Обновляет timestamp диалога (вызывается при отправке нового сообщения)"""
        if dialog_id in self.dialogs:
            # Обновляем время в диалоге
            self.dialogs[dialog_id].updated = datetime.now()
            self._save_dialog(self.dialogs[dialog_id])
            return True
        return False
    
    def add_message(self, dialog_id: str, role: MessageRole, content: str) -> bool:
        """Добавляет сообщение в диалог"""
        if dialog_id in self.dialogs:
            # Добавляем сообщение
            self.dialogs[dialog_id].add_message(role, content)
            # Обновляем timestamp
            self.dialogs[dialog_id].updated = datetime.now()
            self._save_dialog(self.dialogs[dialog_id])
            return True
        return False
    
    def clear_dialog(self, dialog_id: str) -> bool:
        """Очищает историю диалога"""
        if dialog_id in self.dialogs:
            self.dialogs[dialog_id].clear_history()
            self._save_dialog(self.dialogs[dialog_id])
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
                
        except Exception:
            pass
    
    def _save_all_silent(self):
        """Тихое сохранение всех диалогов"""
        for dialog_id, dialog in self.dialogs.items():
            self._save_dialog(dialog)
    
    def load_dialogs(self):
        """Загружает сохраненные диалоги"""
        try:
            if not os.path.exists(self.config.save_dir):
                os.makedirs(self.config.save_dir, exist_ok=True)
                return
            
            dialog_files = []
            for f in os.listdir(self.config.save_dir):
                if f.startswith("dialog_") and f.endswith(".json"):
                    file_path = os.path.join(self.config.save_dir, f)
                    
                    if os.path.getsize(file_path) == 0:
                        os.remove(file_path)
                        continue
                    
                    dialog_files.append(file_path)
            
            for file_path in dialog_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read().strip()
                        
                        if not file_content:
                            os.remove(file_path)
                            continue
                        
                        dialog_data = json.loads(file_content)
                
                    # Существующие поля
                    dialog_data["created"] = datetime.fromisoformat(dialog_data["created"])
                    dialog_data["updated"] = datetime.fromisoformat(dialog_data["updated"])
                    
                    # НОВЫЕ ПОЛЯ: pinned и pinned_position
                    dialog_data["pinned"] = dialog_data.get("pinned", False)
                    dialog_data["pinned_position"] = dialog_data.get("pinned_position")
                    
                    messages = []
                    for msg_data in dialog_data.get("history", []):
                        msg_data["timestamp"] = datetime.fromisoformat(msg_data["timestamp"])
                        msg_data["role"] = MessageRole(msg_data["role"])
                        messages.append(Message(**msg_data))
                    dialog_data["history"] = messages
                    
                    dialog = Dialog(**dialog_data)
                    dialog_id = dialog.id
                    self.dialogs[dialog_id] = dialog
                    
                    dialog_num = int(dialog_id)
                    if dialog_num >= self.next_dialog_id:
                        self.next_dialog_id = dialog_num + 1
                    
                except json.JSONDecodeError:
                    os.remove(file_path)
                except Exception:
                    pass
            
            if self.dialogs:
                dialogs_list = self.get_dialog_list()
                self.current_dialog_id = dialogs_list[0]["id"]
                
        except Exception:
            pass

# Глобальный экземпляр
dialog_service = DialogService()