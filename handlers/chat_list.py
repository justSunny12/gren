# handlers/chat_list.py
import json
from .base import BaseHandler

class ChatListHandler(BaseHandler):
    """Обработчик для получения данных списка чатов"""
    
    def get_chat_list_data(self, scroll_target: str = 'none'):
        """
        Возвращает данные списка чатов с группировкой в формате JSON.
        scroll_target: 'top', 'today', 'none'
        """
        try:
            grouped_dialogs = self.dialog_service.get_dialog_list_with_groups()
            
            js_data = {
                "groups": {},
                "flat": [],
                "_scroll_target": scroll_target   # строка для JS
            }
            
            for group_name, dialogs in grouped_dialogs.items():
                group_dialogs = []
                for d in dialogs:
                    js_dialog = {
                        "id": d['id'],
                        "name": d['name'].replace('\n', ' ').replace('\r', ' '),
                        "history_length": d['history_length'],
                        "updated": d['updated'],
                        "is_current": d['is_current'],
                        "pinned": d.get('pinned', False),
                        "pinned_position": d.get('pinned_position')
                    }
                    group_dialogs.append(js_dialog)
                    js_data["flat"].append(js_dialog)
                
                js_data["groups"][group_name] = group_dialogs
            
            return json.dumps(js_data, ensure_ascii=False)
        except Exception:
            return json.dumps({"groups": {}, "flat": [], "_scroll_target": "none"}, ensure_ascii=False)