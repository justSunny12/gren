# services/chat/manager.py (исправленная версия)
"""
Главный менеджер для координации всех компонентов чата
"""

import asyncio
import threading
import traceback
from typing import AsyncGenerator, List, Dict, Optional, Tuple, Any

from .core import validate_message, sanitize_user_input
from .formatter import format_history_for_model
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
        """Обрабатывает входящее сообщение и асинхронно стримит ответ."""
        from models.enums import MessageRole
        
        # 1. Валидация
        from .core import validate_message, sanitize_user_input
        is_valid, error = validate_message(prompt)
        if not is_valid:
            yield [], error, dialog_id or ""
            return
        
        prompt = sanitize_user_input(prompt)
        
        # 2. Получаем диалог (сообщение пользователя уже должно быть добавлено в MessageHandler)
        dialog = self.operations.dialog_service.get_dialog(dialog_id)
        if not dialog:
            yield [], "Диалог не найден", dialog_id
            return
        
        # 3. Форматируем историю для модели (уже содержит сообщение пользователя)
        from .formatter import format_history_for_model
        formatted_history = format_history_for_model(dialog.history)
        
        # 4. Подготавливаем накопители
        accumulated_response = ""
        suffix_on_stop = "...<генерация прервана пользователем>"
        
        # 5. Запускаем стриминг
        try:
            async for chunk in self.operations.stream_response(
                messages=formatted_history,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            ):
                accumulated_response += chunk
                
                # 6. Yield обновленной истории
                # ИСПРАВЛЕНИЕ: Создаём КОПИЮ базовой истории и добавляем текущий накопленный ответ
                # Это безопасно и не нарушает кэш
                base_history = dialog.to_ui_format()  # Кэшированная базовая история (без ответа ассистента)
                
                # Создаём новый список, чтобы не модифицировать кэш
                history_for_ui = list(base_history)  # Создаём копию списка
                history_for_ui.append({
                    "role": MessageRole.ASSISTANT.value,
                    "content": accumulated_response
                })
                
                yield (history_for_ui, accumulated_response, dialog_id)
            
            # 7. После завершения стрима
            was_stopped = stop_event and stop_event.is_set()
            final_text = accumulated_response
            
            if was_stopped:
                final_text += suffix_on_stop
            
            # 8. Сохраняем финальное сообщение ассистента
            self.operations.dialog_service.add_message(
                dialog_id, 
                MessageRole.ASSISTANT, 
                final_text
            )
            
            # 9. Генерируем название если нужно
            from .naming import generate_simple_name, is_default_name
            config = self.operations.get_config()
            if is_default_name(dialog.name, config):
                new_name = generate_simple_name(prompt, config)
                if new_name and new_name != dialog.name:
                    self.operations.dialog_service.rename_dialog(dialog_id, new_name)
            
            # 10. Финальный yield - используем обновлённый диалог с кэшем
            updated_dialog = self.operations.dialog_service.get_dialog(dialog_id)
            final_history = updated_dialog.to_ui_format()  # Теперь содержит полный ответ ассистента
            yield (final_history, final_text, dialog_id)
            
        except Exception as e:
            print(f"❌ Ошибка в process_message_stream: {e}")
            import traceback
            traceback.print_exc()
            
            # Возвращаем историю с ошибкой
            base_history = dialog.to_ui_format()
            error_history = list(base_history)  # Копируем базовую историю
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
            dialog = self.operations.dialog_service.get_dialog(dialog_id)
        
        if dialog:
            return dialog.to_ui_format()
        return []
    
    # Дополнительные методы для удобства
    def get_formatted_stats(self) -> Dict[str, Any]:
        """Возвращает отформатированную статистику"""
        return self.operations.get_model_stats()