# handlers/chat_list.py
import json
from .base import BaseHandler
from services.user_config_service import user_config_service

class ChatListHandler(BaseHandler):
    def get_chat_list_data(self, scroll_target: str = 'none'):
        try:
            grouped_dialogs = self.dialog_service.get_dialog_list_with_groups()
            user_config = user_config_service.get_user_config(force_reload=True)
            thinking_state = user_config.generation.enable_thinking
            if thinking_state is None:
                thinking_state = False
            js_data = {
                "groups": {},
                "flat": [],
                "_scroll_target": scroll_target,
                "_thinking_state": thinking_state
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
        except Exception as e:
            # Логируем ошибку с полным traceback
            self.logger.exception("Ошибка получения списка чатов: %s", e)
            return json.dumps({
                "groups": {},
                "flat": [],
                "_scroll_target": "none",
                "_thinking_state": False
            }, ensure_ascii=False)