# /logic/ui_handlers.py
import gradio as gr
from container import container

class UIHandlers:
    """Обработчики UI событий"""
    
    def __init__(self):
        # Ленивая загрузка сервисов
        self._chat_service = None
        self._dialog_service = None
        self._config = None
    
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
    def config(self):
        if self._config is None:
            self._config = container.get_config()
        return self._config
    
    def get_dialog_list_for_dropdown(self):
        """Получает список чатов для обновления dropdown"""
        dialogs = self.dialog_service.get_dialog_list()
        
        # Очищаем названия от переносов строк и лишних символов
        chat_names = []
        for d in dialogs:
            # Очищаем название от переносов строк
            clean_name = d['name'].replace('\n', ' ').replace('\r', ' ')
            # Убираем лишние пробелы
            clean_name = ' '.join(clean_name.split())
            # Обрезаем если слишком длинное
            if len(clean_name) > 50:
                clean_name = clean_name[:47] + '...'
            chat_names.append(f"{clean_name} ({d['id']})")
        
        current_dialog = self.dialog_service.get_current_dialog()
        if current_dialog and chat_names:
            current_dialog_id = current_dialog.id
            # Находим индекс текущего диалога
            current_index = 0
            for i, d in enumerate(dialogs):
                if d["id"] == current_dialog_id:
                    current_index = i
                    break
            return gr.update(choices=chat_names, value=chat_names[current_index])
        return gr.update(choices=chat_names)
    
    def get_chat_name_from_selection(self, selection=None):
        """Получает название чата из выбранного элемента dropdown"""
        if selection:
            try:
                chat_name = selection.split("(")[0].strip()
                return chat_name
            except:
                return "Чат"
        elif self.dialog_service.current_dialog_id:
            dialog = self.dialog_service.get_current_dialog()
            if dialog:
                return dialog.name
        return "Чат"
    
    def create_chat_handler(self):
        """Обработчик создания нового чата"""
        try:
            dialog_id = self.dialog_service.create_dialog()
            
            dialogs = self.dialog_service.get_dialog_list()
            chat_names = [f"{d['name']} ({d['id']})" for d in dialogs]
            
            current_index = 0
            for i, d in enumerate(dialogs):
                if d["id"] == dialog_id:
                    current_index = i
                    break
            
            dialog = self.dialog_service.get_dialog(dialog_id)
            chat_name = dialog.name if dialog else "Новый чат"
            
            return [], "", dialog_id, gr.update(choices=chat_names, value=chat_names[current_index]), f"✅ Создан чат: {chat_name}", gr.update(label=chat_name)
        except Exception as e:
            print(f"Ошибка при создании чата: {e}")
            return [], "", None, gr.update(), f"⚠️ Ошибка: {str(e)}", gr.update()
    
    def switch_chat_handler(self, selection):
        """Обработчик переключения чата"""
        try:
            if not selection:
                return [], "", None, gr.update(), "⚠️ Выберите чат", gr.update()
            
            dialog_id = selection.split("(")[-1].rstrip(")")
            
            if self.dialog_service.switch_dialog(dialog_id):
                dialog = self.dialog_service.get_dialog(dialog_id)
                history = self.chat_service.get_chat_history(dialog_id)
                
                dialogs = self.dialog_service.get_dialog_list()
                chat_names = [f"{d['name']} ({d['id']})" for d in dialogs]
                
                current_index = 0
                for i, d in enumerate(dialogs):
                    if d["id"] == dialog_id:
                        current_index = i
                        break
                
                chat_name = dialog.name if dialog else "Чат"
                return history, "", dialog_id, gr.update(choices=chat_names, value=chat_names[current_index]), f"✅ Переключено на: {chat_name}", gr.update(label=chat_name)
            
            return [], "", None, gr.update(), "⚠️ Ошибка переключения чата", gr.update()
        except Exception as e:
            print(f"Ошибка при переключении чата: {e}")
            return [], "", None, gr.update(), f"⚠️ Ошибка: {str(e)}", gr.update()
    
    def delete_chat_handler(self, selection):
        """Обработчик удаления чата"""
        try:
            if not selection:
                return [], "", None, gr.update(), "⚠️ Выберите чат для удаления", gr.update()
            
            dialog_id = selection.split("(")[-1].rstrip(")")
            
            dialog = self.dialog_service.get_dialog(dialog_id)
            if not dialog:
                return [], "", None, gr.update(), "⚠️ Чат не найден", gr.update()
            
            dialog_name = dialog.name
            
            if self.dialog_service.delete_dialog(dialog_id):
                dialogs = self.dialog_service.get_dialog_list()
                chat_names = [f"{d['name']} ({d['id']})" for d in dialogs] if dialogs else []
                
                if dialogs:
                    current_index = 0
                    new_dialog_id = dialogs[0]["id"]
                    history = self.chat_service.get_chat_history(new_dialog_id)
                    dropdown_value = chat_names[current_index]
                    chat_name = dialogs[0]["name"]
                else:
                    current_index = 0
                    new_dialog_id = None
                    history = []
                    dropdown_value = None
                    chat_name = "Чат"
                
                return history, "", new_dialog_id, gr.update(choices=chat_names, value=dropdown_value), f"✅ Удален чат: {dialog_name}", gr.update(label=chat_name)
            
            return [], "", None, gr.update(), "⚠️ Ошибка удаления чата", gr.update()
        except Exception as e:
            print(f"Ошибка при удалении чата: {e}")
            return [], "", None, gr.update(), f"⚠️ Ошибка: {str(e)}", gr.update()
    
    def send_message_handler(self, prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Обработчик отправки сообщения"""
        try:
            if not prompt.strip():
                return [], "", chat_id or "", gr.update(), gr.update()
            
            # Убедимся что enable_thinking булево
            if enable_thinking is None:
                enable_thinking = False
            
            print(f"📨 Отправка сообщения (thinking: {enable_thinking})")
            
            # Получаем или создаем диалог
            if not chat_id:
                chat_id = self.dialog_service.create_dialog()
            
            # Обрабатываем сообщение
            history, _, new_chat_id = self.chat_service.process_message(
                prompt, chat_id, max_tokens, temperature, enable_thinking
            )
            
            # Обновляем список чатов
            dialogs = self.dialog_service.get_dialog_list()
            chat_names = [f"{d['name']} ({d['id']})" for d in dialogs]
            
            # Находим индекс текущего чата
            current_index = 0
            for i, d in enumerate(dialogs):
                if d["id"] == new_chat_id:
                    current_index = i
                    break
            
            chat_name = self.get_chat_name_from_selection(chat_names[current_index])
            
            return history, "", new_chat_id, gr.update(choices=chat_names, value=chat_names[current_index]), gr.update(label=chat_name)
        
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")
            return [], "", chat_id or "", gr.update(), gr.update()
    
    def init_app_handler(self):
        """Обработчик инициализации приложения"""
        try:
            # Создаем первый чат, если нет существующих
            if not self.dialog_service.dialogs:
                chat_id = self.dialog_service.create_dialog()
            else:
                chat_id = self.dialog_service.current_dialog_id
            
            # Получаем историю текущего чата
            history = self.chat_service.get_chat_history(chat_id)
            
            # Получаем обновленный список чатов для dropdown
            dropdown = self.get_dialog_list_for_dropdown()
            
            # Получаем название текущего чата
            chat_name = "Чат"
            if chat_id:
                dialog = self.dialog_service.get_dialog(chat_id)
                if dialog:
                    # Очищаем название от переносов строк
                    chat_name = dialog.name.replace('\n', ' ').replace('\r', ' ')
                    chat_name = ' '.join(chat_name.split())
                    if len(chat_name) > 30:
                        chat_name = chat_name[:27] + '...'
            
            return history, chat_id, dropdown, gr.update(label=chat_name)
        except Exception as e:
            print(f"Ошибка при инициализации приложения: {e}")
            return [], None, gr.update(), gr.update()

# Глобальный экземпляр
ui_handlers = UIHandlers()