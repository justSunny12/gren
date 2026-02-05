"""
Группировка диалогов по датам
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Any
from models.dialog import Dialog


class DialogGrouper:
    """Группировка диалогов для отображения"""
    
    @staticmethod
    def get_dialog_list(dialogs: Dict[str, Dialog], 
                       current_dialog_id: str) -> List[Dict[str, Any]]:
        """Получает список всех диалогов"""
        dialogs_list = []
        for dialog_id, dialog in dialogs.items():
            dialog_info = {
                "id": dialog_id,
                "name": dialog.name,
                "history_length": len(dialog.history),
                "created": dialog.created.isoformat(),
                "updated": dialog.updated.isoformat(),
                "is_current": (dialog_id == current_dialog_id),
                "pinned": dialog.pinned,
                "pinned_position": dialog.pinned_position
            }
            dialogs_list.append(dialog_info)
        
        # Сортировка: закрепленные → обычные
        dialogs_list.sort(key=lambda x: (
            -1 if x["pinned"] else 0,
            x["pinned_position"] if x["pinned"] and x["pinned_position"] is not None else 999,
            x["updated"]
        ), reverse=True)
        
        return dialogs_list
    
    @staticmethod
    def get_dialog_list_with_groups(dialogs: Dict[str, Dialog],
                                   current_dialog_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Группирует диалоги по категориям"""
        dialogs_list = DialogGrouper.get_dialog_list(dialogs, current_dialog_id)
        
        today_date = date.today()
        yesterday_date = today_date - timedelta(days=1)
        week_ago_date = today_date - timedelta(days=7)
        month_ago_date = today_date - timedelta(days=30)
        
        groups = {
            "pinned": [],
            "today": [],
            "yesterday": [],
            "week": [],
            "month": [],
            "older": []
        }
        
        for dialog_info in dialogs_list:
            if dialog_info.get("pinned", False):
                groups["pinned"].append(dialog_info)
                continue
            
            try:
                last_update = datetime.fromisoformat(dialog_info["updated"].replace('Z', '+00:00'))
                last_update_date = last_update.date()
                
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
        
        # Сортировка закрепленных
        if groups["pinned"]:
            groups["pinned"].sort(key=lambda x: x.get("pinned_position", 999))
        
        # Формируем результат
        result = {}
        group_mapping = {
            "pinned": "Закрепленные",
            "today": "Сегодня", 
            "yesterday": "Вчера",
            "week": "7 дней",
            "month": "Месяц",
            "older": "Более месяца"
        }
        
        for group_key, group_data in groups.items():
            if group_data:
                result[group_mapping[group_key]] = group_data
        
        return result