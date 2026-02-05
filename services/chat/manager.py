# services/chat/manager.py
"""
Главный менеджер для координации всех компонентов чата
"""

import asyncio
import threading
import traceback
from typing import AsyncGenerator, List, Dict, Optional, Tuple, Any

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
        
    async def process_message_stream(
        self,
        prompt: str,
        dialog_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        stop_event: Optional[threading.Event] = None
    ) -> AsyncGenerator[Tuple[List[Dict], str, str], None]:
        """Обрабатывает входящее сообщение и асинхронно стримит ответ.
        
        Yields:
            Кортеж (history, accumulated_text, current_dialog_id):
            - history: история для UI (список сообщений) с накопленным ответом
            - accumulated_text: текущий накопленный текст ответа ассистента
            - current_dialog_id: ID диалога
        """
        from models.enums import MessageRole
        
        # 1. Валидация
        from .core import validate_message, sanitize_user_input
        is_valid, error = validate_message(prompt)
        if not is_valid:
            yield [], error, dialog_id or ""
            return
        
        prompt = sanitize_user_input(prompt)
        
        # 2. Получаем/создаем диалог
        if not dialog_id:
            dialog_id = self.operations.create_dialog()
        
        dialog = self.operations.get_dialog(dialog_id)
        if not dialog:
            yield [], "Диалог не найден", dialog_id
            return
        
        # 3. НЕМЕДЛЕННО добавляем сообщение пользователя
        self.operations.dialog_service.add_message(dialog_id, MessageRole.USER, prompt)
        dialog = self.operations.get_dialog(dialog_id)  # Обновляем ссылку
        
        # 4. Форматируем историю для модели
        from .formatter import format_history_for_model, format_history_for_ui
        formatted_history = format_history_for_model(dialog.history)
        
        # 5. Подготавливаем накопители
        accumulated_response = ""
        suffix_on_stop = "...<генерация прервана пользователем>"
        
        # 6. Запускаем стриминг
        try:
            async for chunk in self.operations.stream_response(
                messages=formatted_history,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            ):
                accumulated_response += chunk
                
                # 7. Yield обновленной истории (вариант B: только последнее сообщение)
                # Создаем историю: все старые сообщения + текущий накопленный ответ
                history_for_ui = format_history_for_ui(dialog.history)
                history_for_ui.append({
                    "role": MessageRole.ASSISTANT.value,
                    "content": accumulated_response
                })
                
                yield (history_for_ui, accumulated_response, dialog_id)
            
            # 8. После завершения стрима
            was_stopped = stop_event and stop_event.is_set()
            final_text = accumulated_response
            
            if was_stopped:
                final_text += suffix_on_stop
            
            # 9. Сохраняем финальное сообщение ассистента
            self.operations.dialog_service.add_message(
                dialog_id, 
                MessageRole.ASSISTANT, 
                final_text
            )
            
            # 10. Генерируем название если нужно
            from .naming import generate_simple_name, is_default_name
            config = self.operations.get_config()
            if is_default_name(dialog.name, config):
                new_name = generate_simple_name(prompt, config)
                if new_name and new_name != dialog.name:
                    self.operations.rename_dialog(dialog_id, new_name)
            
            # 11. Финальный yield
            updated_dialog = self.operations.get_dialog(dialog_id)
            final_history = format_history_for_ui(updated_dialog.history)
            yield (final_history, final_text, dialog_id)
            
        except Exception as e:
            print(f"❌ Ошибка в process_message_stream: {e}")
            import traceback
            traceback.print_exc()
            
            # Возвращаем историю с ошибкой
            error_history = format_history_for_ui(dialog.history)
            error_history.append({
                "role": MessageRole.ASSISTANT.value,
                "content": f"⚠️ Ошибка: {str(e)[:100]}"
            })
            yield (error_history, "", dialog_id)
    
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