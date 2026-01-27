# /logic/ui_handlers.py - исправляем обработчики
import gradio as gr
from container import container
import time
import json

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
        """Возвращает данные списка чатов в формате JSON"""
        try:
            dialogs = self.dialog_service.get_dialog_list()
            
            js_dialogs = []
            for d in dialogs:
                js_dialogs.append({
                    "id": d['id'],
                    "name": d['name'].replace('\n', ' ').replace('\r', ' '),
                    "history_length": d['history_length'],
                    "updated": d['updated'],
                    "is_current": d['is_current']
                })
            
            return json.dumps(js_dialogs, ensure_ascii=False)
        except Exception:
            return json.dumps([], ensure_ascii=False)
    
    def handle_chat_selection(self, chat_id: str):
        """Обработчик выбора чата из списка"""
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
    
    def delete_chat_with_js_handler(self):
        """Обработчик удаления текущего чата с правильной логикой переключения"""
        try:
            current_dialog = self.dialog_service.get_current_dialog()
            if not current_dialog:
                return [], "", None, "⚠️ Нет активного чата", gr.HTML(""), "[]"
            
            dialog_id = current_dialog.id
            dialog_name = current_dialog.name
            
            # Получаем список всех диалогов ДО удаления
            all_dialogs = self.dialog_service.get_dialog_list()
            current_index = -1
            for i, d in enumerate(all_dialogs):
                if d['id'] == dialog_id:
                    current_index = i
                    break
            
            # Удаляем текущий диалог
            if self.dialog_service.delete_dialog(dialog_id):
                # Диалог уже удален, логика переключения уже выполнена в dialog_service
                # Просто получаем новый текущий диалог
                new_dialog = self.dialog_service.get_current_dialog()
                if new_dialog:
                    new_history = new_dialog.to_ui_format()
                    new_dialog_id = new_dialog.id
                    status_text = f"✅ Удален чат: {dialog_name}. Открыт: {new_dialog.name}"
                else:
                    new_history = []
                    new_dialog_id = None
                    status_text = f"✅ Удален чат: {dialog_name}. Создайте новый чат."
                
                chat_list_data = self.get_chat_list_data()
                
                js_code = f"""
                <script>
                setTimeout(() => {{
                    document.dispatchEvent(new Event('chatListUpdated'));
                }}, 100);
                </script>
                """
                
                return new_history, "", new_dialog_id, status_text, gr.HTML(js_code), chat_list_data
            
            return [], "", dialog_id, "⚠️ Ошибка удаления чата", gr.HTML(""), self.get_chat_list_data()
            
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