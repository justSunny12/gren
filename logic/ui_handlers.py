# /logic/ui_handlers.py
import gradio as gr
from container import container
import time
import json
import urllib.parse

class UIHandlers:
    """Обработчики UI событий"""
    
    def __init__(self):
        # Ленивая загрузка сервисов
        self._chat_service = None
        self._dialog_service = None
        self._config_service = None
        self._last_save_time = 0
        self._save_debounce_ms = 500
        self._pending_save = None
        self._last_chat_switch = 0  # Защита от быстрого переключения
        self._switch_debounce_ms = 300
    
    @property
    def chat_service(self):
        if self._chat_service is None:
            self._chat_service = container.get_chat_service()
        return self._chat_service
    
    @property
    def dialog_service(self):
        if self._dialog_service is None:
            self._dialog_service = container.get_dialog_service()
        return self._dialog_service
    
    @property
    def config_service(self):
        if self._config_service is None:
            self._config_service = container.get("config_service")
        return self._config_service
    
    @property
    def config(self):
        return self.config_service.get_config()
    
    def get_chat_list_data(self):
        """Возвращает данные списка чатов с группировкой в формате JSON"""
        try:
            # Получаем диалоги с группировкой по датам
            grouped_dialogs = self.dialog_service.get_dialog_list_with_groups()
            
            # Преобразуем в формат для фронтенда
            js_data = {
                "groups": {},
                "flat": []
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
            return json.dumps({"groups": {}, "flat": []}, ensure_ascii=False)
    
    def handle_chat_selection(self, chat_id: str):
        """Обработчик выбора чата из списка"""
        # Проверяем, не запрос ли это на удаление
        if chat_id and chat_id.startswith('delete:'):
            return self.handle_chat_deletion(chat_id)
        
        # Проверяем, не запрос ли это на переименование
        if chat_id and chat_id.startswith('rename:'):
            return self.handle_chat_rename(chat_id)
        
        # Проверяем, не запрос ли это на закрепление/открепление
        if chat_id and (chat_id.startswith('pin:') or chat_id.startswith('unpin:')):
            return self.handle_chat_pinning(chat_id)
        
        current_time = time.time() * 1000
        
        # Защита от быстрого переключения
        if current_time - self._last_chat_switch < self._switch_debounce_ms:
            # Возвращаем текущее состояние без изменений
            current_dialog = self.dialog_service.get_current_dialog()
            if current_dialog:
                history = current_dialog.to_ui_format()
                current_id = current_dialog.id
                status_text = f"⏳ Слишком быстро..."
                chat_list_data = self.get_chat_list_data()
                return history, current_id, status_text, chat_list_data
            else:
                return [], "", "⚠️ Нет активного чата", self.get_chat_list_data()
        
        self._last_chat_switch = current_time
        chat_id = chat_id.strip()
        
        if not chat_id or chat_id == "null" or chat_id == "undefined":
            return [], "", "⚠️ Неверный ID чата", self.get_chat_list_data()
        
        if self.dialog_service.switch_dialog(chat_id):
            dialog = self.dialog_service.get_dialog(chat_id)
            history = dialog.to_ui_format() if dialog else []
            status_text = f"✅ Переключен на: {dialog.name if dialog else chat_id}"
            chat_list_data = self.get_chat_list_data()
            return history, chat_id, status_text, chat_list_data
        else:
            return [], chat_id, f"⚠️ Ошибка переключения на: {chat_id}", self.get_chat_list_data()
    
    def handle_chat_pinning(self, pin_command: str):
        """Обработчик закрепления/открепления чата"""
        try:
            # Парсим команду: "pin:<chat_id>:<action>" где action = pin/unpin
            parts = pin_command.split(':')
            if len(parts) != 3:
                return [], "", "⚠️ Неверный формат команды", self.get_chat_list_data()
            
            action_type = parts[0]  # pin или unpin
            chat_id = parts[1]
            action = parts[2]  # тоже pin или unpin
            
            # Проверяем согласованность
            if action_type != action:
                return [], "", "⚠️ Несогласованные действия", self.get_chat_list_data()
            
            # Получаем информацию о чате
            dialog = self.dialog_service.get_dialog(chat_id)
            if not dialog:
                return [], "", "⚠️ Чат не найден", self.get_chat_list_data()
            
            chat_name = dialog.name
            
            if action == 'pin':
                # Закрепляем чат
                success = self.dialog_service.pin_dialog(chat_id)
                if success:
                    status_text = f"📌 Чат закреплен: {chat_name}"
                else:
                    status_text = f"⚠️ Ошибка закрепления чата: {chat_name}"
            else:  # unpin
                # Открепляем чат
                success = self.dialog_service.unpin_dialog(chat_id)
                if success:
                    status_text = f"📌 Чат откреплен: {chat_name}"
                else:
                    status_text = f"⚠️ Ошибка открепления чата: {chat_name}"
            
            # Получаем обновленный диалог
            updated_dialog = self.dialog_service.get_dialog(chat_id)
            
            # Формируем ответ
            if updated_dialog:
                history = updated_dialog.to_ui_format()
            else:
                history = []
            
            chat_list_data = self.get_chat_list_data()
            return history, chat_id, status_text, chat_list_data
            
        except Exception as e:
            return [], "", f"⚠️ Ошибка при закреплении/откреплении: {str(e)}", self.get_chat_list_data()
    
    def handle_chat_deletion(self, delete_command: str):
        """Обработчик удаления чата из контекстного меню"""
        try:
            # Парсим команду: "delete:<chat_id>:<is_active>"
            parts = delete_command.split(':')
            if len(parts) != 3 or parts[0] != 'delete':
                return [], "", "⚠️ Неверный формат команды", self.get_chat_list_data()
            
            chat_id = parts[1]
            is_active = parts[2] == 'active'
            
            # Получаем информацию о чате перед удалением
            dialog_to_delete = self.dialog_service.get_dialog(chat_id)
            if not dialog_to_delete:
                return [], "", "⚠️ Чат не найден", self.get_chat_list_data()
            
            chat_name = dialog_to_delete.name
            
            # Получаем текущий активный чат ДО удаления
            current_before = self.dialog_service.get_current_dialog()
            current_id_before = current_before.id if current_before else None
            
            # Проверяем, активный ли чат удаляем (по current_dialog_id)
            is_currently_active = (current_id_before == chat_id)
            
            # Удаляем чат с соответствующей стратегией
            # keep_current=True только если удаляем НЕактивный чат
            keep_current = not is_currently_active
            
            success = self.dialog_service.delete_dialog(
                chat_id, 
                keep_current=keep_current
            )
            
            if not success:
                return [], "", f"⚠️ Ошибка удаления чата: {chat_name}", self.get_chat_list_data()
            
            # Получаем состояние ПОСЛЕ удаления
            current_after = self.dialog_service.get_current_dialog()
            
            # Формируем ответ
            if current_after:
                history = current_after.to_ui_format()
                new_id = current_after.id
                
                # Формируем сообщение в зависимости от ситуации
                if is_currently_active:
                    # Удалили активный чат
                    status_text = f"✅ Удален активный чат: {chat_name}. Открыт: {current_after.name}"
                else:
                    # Удалили неактивный чат - остаемся в текущем
                    if current_after.id == current_id_before:
                        status_text = f"✅ Удален неактивный чат: {chat_name}. Остаемся в: {current_after.name}"
                    else:
                        status_text = f"✅ Удален чат: {chat_name}. Открыт: {current_after.name}"
            else:
                # Нет активного чата (удалили последний)
                history = []
                new_id = ""
                status_text = f"✅ Удален последний чат: {chat_name}. Создайте новый чат"
            
            chat_list_data = self.get_chat_list_data()
            return history, new_id, status_text, chat_list_data
            
        except Exception as e:
            return [], "", f"⚠️ Ошибка при удалении: {str(e)}", self.get_chat_list_data()
    
    def handle_chat_rename(self, rename_command: str):
        """Обработчик переименования чата из контекстного меню"""
        try:
            # Парсим команду: "rename:<chat_id>:<new_name>"
            parts = rename_command.split(':', 2)  # Разделяем только на 3 части
            if len(parts) != 3 or parts[0] != 'rename':
                return [], "", "⚠️ Неверный формат команды переименования", self.get_chat_list_data()
            
            chat_id = parts[1]
            new_name = urllib.parse.unquote(parts[2])
            
            # Получаем информацию о чате перед переименованием
            dialog_to_rename = self.dialog_service.get_dialog(chat_id)
            if not dialog_to_rename:
                return [], "", "⚠️ Чат не найден", self.get_chat_list_data()
            
            old_name = dialog_to_rename.name
            
            # Проверяем новое название
            if not new_name or not new_name.strip():
                return [], "", "⚠️ Название не может быть пустым", self.get_chat_list_data()
            
            # Обрезаем если слишком длинное
            if len(new_name) > 50:
                new_name = new_name[:50]
            
            # Переименовываем
            success = self.dialog_service.rename_dialog(chat_id, new_name)
            
            if not success:
                return [], "", f"⚠️ Ошибка переименования чата: {old_name}", self.get_chat_list_data()
            
            # Получаем обновленный диалог
            updated_dialog = self.dialog_service.get_dialog(chat_id)
            
            # Формируем ответ
            if updated_dialog:
                history = updated_dialog.to_ui_format()
                status_text = f"✅ Чат переименован: {old_name} → {new_name}"
            else:
                history = []
                status_text = f"⚠️ Чат не найден после переименования"
            
            chat_list_data = self.get_chat_list_data()
            return history, chat_id, status_text, chat_list_data
            
        except Exception as e:
            return [], "", f"⚠️ Ошибка при переименовании: {str(e)}", self.get_chat_list_data()
    
    def create_chat_with_js_handler(self):
        """Обработчик создания нового чата без лишних задержек"""
        try:
            dialog_id = self.dialog_service.create_dialog()
            dialog = self.dialog_service.get_dialog(dialog_id)
            
            chat_list_data = self.get_chat_list_data()
            
            js_code = f"""
            <script>
            document.dispatchEvent(new Event('chatListUpdated'));
            </script>
            """
            
            history = dialog.to_ui_format()
            status_text = f"✅ Создан чат: {dialog.name}"
            
            return history, "", dialog_id, status_text, gr.HTML(js_code), chat_list_data
            
        except Exception as e:
            return [], "", None, f"⚠️ Ошибка: {str(e)}", gr.HTML(""), "[]"
    
    def send_message_handler(self, prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Обработчик отправки сообщения"""
        try:
            if not prompt.strip():
                return [], "", chat_id or "", gr.update(), self.get_chat_list_data()
            
            if not chat_id:
                chat_id = self.dialog_service.create_dialog()
            
            history, _, new_chat_id = self.chat_service.process_message(
                prompt, chat_id, max_tokens, temperature, enable_thinking
            )
            
            chat_list_data = self.get_chat_list_data()
            chat_name = self.get_chat_name_from_id(new_chat_id)
            
            return history, "", new_chat_id, gr.update(label=chat_name), chat_list_data
        
        except Exception:
            return [], "", chat_id or "", gr.update(), self.get_chat_list_data()
    
    def get_chat_name_from_id(self, dialog_id: str) -> str:
        """Получает название чата по ID"""
        if not dialog_id:
            return "Чат"
        
        dialog = self.dialog_service.get_dialog(dialog_id)
        if dialog:
            chat_name = dialog.name.replace('\n', ' ').replace('\r', ' ')
            chat_name = ' '.join(chat_name.split())
            if len(chat_name) > 30:
                chat_name = chat_name[:27] + '...'
            return chat_name
        return "Чат"
    
    def save_user_settings_handler(self, max_tokens: int, temperature: float, enable_thinking: bool):
        """Обработчик сохранения настроек (с debounce)"""
        current_time = time.time() * 1000
        
        if self._pending_save:
            self._pending_save = None
        
        if current_time - self._last_save_time > self._save_debounce_ms:
            try:
                self.config_service.update_user_setting("generation", "max_tokens", max_tokens)
                self.config_service.update_user_setting("generation", "temperature", temperature)
                self.config_service.update_user_setting("generation", "enable_thinking", enable_thinking)
                self._last_save_time = current_time
                return "✅ Настройки сохранены"
            except Exception as e:
                return f"⚠️ Ошибка: {str(e)}"
        else:
            self._pending_save = (max_tokens, temperature, enable_thinking, current_time)
            return "⏳ Сохранение..."
    
    def load_user_settings(self):
        """Загружает пользовательские настройки"""
        try:
            config = self.config
            return (
                config.generation.default_max_tokens,
                config.generation.default_temperature,
                config.generation.default_enable_thinking
            )
        except Exception:
            gen_config = self.config_service.get_default_config().generation
            return (
                gen_config.default_max_tokens,
                gen_config.default_temperature,
                gen_config.default_enable_thinking
            )
    
    def init_app_handler(self):
        """Обработчик инициализации приложения"""
        try:
            if not self.dialog_service.dialogs:
                chat_id = self.dialog_service.create_dialog()
            else:
                chat_id = self.dialog_service.current_dialog_id
            
            history = self.chat_service.get_chat_history(chat_id)
            chat_name = self.get_chat_name_from_id(chat_id)
            chat_list_data = self.get_chat_list_data()
            max_tokens, temperature, enable_thinking = self.load_user_settings()
            
            return history, chat_id, gr.update(label=chat_name), max_tokens, temperature, enable_thinking, chat_list_data
            
        except Exception:
            gen_config = self.config_service.get_default_config().generation
            return [], None, gr.update(), gen_config.default_max_tokens, gen_config.default_temperature, gen_config.default_enable_thinking, "[]"

# Глобальный экземпляр
ui_handlers = UIHandlers()