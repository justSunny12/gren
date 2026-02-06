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
    
    # Дополнительные методы для удобства
    def get_formatted_stats(self) -> Dict[str, Any]:
        """Возвращает отформатированную статистику"""
        return self.operations.get_model_stats()
    
    async def stream_response_only(
        self,
        messages: List[Dict[str, str]],
        dialog_id: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        stop_event: Optional[threading.Event] = None
    ) -> AsyncGenerator[Tuple[List[Dict], str, str], None]:
        """Стримит только ответ модели (без добавления сообщения пользователя)"""
        from models.enums import MessageRole
        from .formatter import format_history_for_ui
                
        # Получаем диалог
        dialog = self.operations.get_dialog(dialog_id)
        if not dialog:
            print(f"❌ [ChatManager.stream_response_only] Диалог {dialog_id} не найден")
            return
        
        # Подготавливаем накопители
        accumulated_response = ""
        
        try:
            # Запускаем стриминг ответа модели
            async for chunk in self.operations.stream_response(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            ):
                accumulated_response += chunk
                
                # Создаем временную историю для yield
                temp_dialog = dialog
                # Создаем временную историю: все старые сообщения + текущий накопленный ответ
                temp_history = format_history_for_ui(temp_dialog.history)
                temp_history.append({
                    "role": MessageRole.ASSISTANT.value,
                    "content": accumulated_response
                })
                
                yield temp_history, accumulated_response, dialog_id
            
            # После завершения стрима
            was_stopped = stop_event and stop_event.is_set()
            final_text = accumulated_response
            
            if was_stopped:
                final_text += "...<генерация прервана пользователем>"
            
            # Сохраняем финальное сообщение ассистента
            self.operations.dialog_service.add_message(
                dialog_id, 
                MessageRole.ASSISTANT, 
                final_text
            )
            
            # Генерируем название если нужно
            from .naming import generate_simple_name, is_default_name
            config = self.operations.get_config()
            if is_default_name(dialog.name, config):
                # Берем последнее сообщение пользователя для генерации названия
                user_messages = [msg for msg in dialog.history if msg.role == MessageRole.USER]
                if user_messages:
                    last_user_message = user_messages[-1].content
                    new_name = generate_simple_name(last_user_message, config)
                    if new_name and new_name != dialog.name:
                        self.operations.rename_dialog(dialog_id, new_name)
                        
            # Финальный yield с полной историей
            updated_dialog = self.operations.get_dialog(dialog_id)
            final_history = format_history_for_ui(updated_dialog.history)
            yield final_history, final_text, dialog_id
            
        except Exception as e:
            print(f"❌ [ChatManager.stream_response_only] Ошибка: {e}")
            import traceback
            traceback.print_exc()
            
            # Возвращаем историю с ошибкой
            error_history = format_history_for_ui(dialog.history)
            error_history.append({
                "role": MessageRole.ASSISTANT.value,
                "content": f"⚠️ Ошибка генерации: {str(e)[:100]}"
            })
            yield error_history, "", dialog_id