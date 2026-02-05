# services/chat/manager.py
"""
Главный менеджер для координации всех компонентов чата
"""

import traceback
from typing import List, Dict, Optional, Tuple, Any

from .core import validate_message, sanitize_user_input
from .formatter import format_history_for_model, format_history_for_ui
from .naming import generate_simple_name, is_default_name
from .operations import ChatOperations


class ChatManager:
    """Главный менеджер для работы с чатом"""
    
    def __init__(self):
        self.operations = ChatOperations()
    
    def process_message(self, 
                       prompt: str, 
                       dialog_id: Optional[str] = None,
                       max_tokens: Optional[int] = None,
                       temperature: Optional[float] = None,
                       enable_thinking: Optional[bool] = None) -> Tuple[List[Dict], str, str]:
        """Обрабатывает входящее сообщение"""
        try:
            # 1. Валидация и очистка (pure)
            is_valid, error = validate_message(prompt)
            if not is_valid:
                return [], error, dialog_id or ""
            
            prompt = sanitize_user_input(prompt)
            
            # 2. Получаем/создаем диалог (stateful)
            dialog_id = dialog_id or self.operations.create_dialog()
            dialog = self.operations.get_dialog(dialog_id)
            
            if not dialog:
                return [], "Ошибка: диалог не найден", dialog_id
            
            # 3. Форматируем историю для модели (pure)
            formatted_history = format_history_for_model(dialog.history)
            formatted_history.append({"role": "user", "content": prompt})
            
            # 4. Генерируем ответ (stateful)
            response_text = self.operations.generate_response(
                messages=formatted_history,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking
            )
            
            # 5. Сохраняем сообщения (stateful)
            self.operations.add_messages(dialog_id, prompt, response_text)
            
            # 6. Генерируем название если нужно
            config = self.operations.get_config()
            if is_default_name(dialog.name, config):
                new_name = generate_simple_name(prompt, config)
                if new_name and new_name != dialog.name:
                    self.operations.rename_dialog(dialog_id, new_name)
            
            # 7. Возвращаем отформатированный результат
            updated_dialog = self.operations.get_dialog(dialog_id)
            return format_history_for_ui(updated_dialog.history), "", dialog_id
            
        except Exception as e:
            print(f"❌ Ошибка в process_message: {e}")
            traceback.print_exc()
            return [], f"⚠️ Ошибка: {str(e)[:100]}", dialog_id or ""
    
    def get_chat_history(self, dialog_id: Optional[str] = None) -> List[Dict]:
        """Получает историю чата"""
        if not dialog_id:
            dialog = self.operations.dialog_service.get_current_dialog()
        else:
            dialog = self.operations.get_dialog(dialog_id)
        
        if dialog:
            from .formatter import format_history_for_ui
            return format_history_for_ui(dialog.history)
        return []
    
    def get_stats(self) -> Dict[str, any]:
        """Возвращает статистику"""
        return self.operations.get_model_stats()
    
    # Методы для обратной совместимости с UI
    def send_message_handler(self, prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Обработчик для UI"""
        try:
            if not prompt.strip():
                return [], "", chat_id or "", self.operations.get_chat_list_data()
            
            prompt = sanitize_user_input(prompt)
            
            history, _, new_chat_id = self.process_message(
                prompt, chat_id, max_tokens, temperature, enable_thinking
            )
            
            chat_list_data = self.operations.get_chat_list_data()
            return history, "", new_chat_id, chat_list_data
            
        except Exception as e:
            print(f"❌ Ошибка в send_message_handler: {e}")
            return [], "", chat_id or "", self.operations.get_chat_list_data()
    
    # Дополнительные методы для удобства
    def get_formatted_stats(self) -> Dict[str, Any]:
        """Возвращает отформатированную статистику"""
        return self.operations.get_model_stats()