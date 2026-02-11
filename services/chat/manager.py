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
        self._partial_update_cache = {}
    
    async def process_message_stream(
        self,
        prompt: str,
        dialog_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        stop_event: Optional[threading.Event] = None,
        messages_for_model: Optional[List[Dict[str, str]]] = None  # Новый параметр
    ) -> AsyncGenerator[Tuple[List[Dict], str, str], None]:
        """Обрабатывает входящее сообщение и асинхронно стримит ответ с батчингом."""
        from models.enums import MessageRole
        
        # 1. Валидация
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
        
        # 3. Получаем конфигурацию для проверки названия
        config = self.operations.get_config()
        
        # 4. Форматируем историю для модели (используем переданные сообщения или форматируем сами)
        if messages_for_model is not None:
            formatted_history = messages_for_model
        else:
            formatted_history = format_history_for_model(dialog.history)
        
        # 5. Подготавливаем накопители
        accumulated_response = ""
        suffix_on_stop = "...<генерация прервана пользователем>"
        
        # 6. Кешируем базовую историю для быстрых partial updates
        base_history = dialog.to_ui_format()
        cache_key = f"{dialog_id}_{len(base_history)}"
        
        try:
            async for batch in self.operations.stream_response(
                messages=formatted_history,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            ):
                accumulated_response += batch
                
                # 7. Быстрый partial update без полного копирования истории
                history_for_ui = self._get_cached_history(cache_key, base_history)
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
            
            # 10. Добавляем взаимодействие в контекст
            try:
                dialog.add_interaction_to_context(prompt, final_text)
            except Exception as e:
                print(f"⚠️ Ошибка при добавлении взаимодействия в контекст: {e}")
            
            # 11. Сохраняем состояние контекста
            try:
                dialog.save_context_state()
            except Exception as e:
                print(f"⚠️ Ошибка при сохранении состояния контекста: {e}")
            
            # 12. Генерируем название если нужно
            if is_default_name(dialog.name, config):
                new_name = generate_simple_name(prompt, config)
                if new_name and new_name != dialog.name:
                    self.operations.dialog_service.rename_dialog(dialog_id, new_name)
            
            # 13. Финальный yield - используем обновлённый диалог с кэшем
            updated_dialog = self.operations.dialog_service.get_dialog(dialog_id)
            final_history = updated_dialog.to_ui_format()
            yield (final_history, final_text, dialog_id)
            
            # 14. Очищаем кэш
            self._clear_cache(cache_key)
            
        except Exception as e:
            print(f"❌ Ошибка в process_message_stream: {e}")
            import traceback
            traceback.print_exc()
            
            # Очищаем кэш при ошибке
            self._clear_cache(cache_key)
            
            # Возвращаем историю с ошибкой
            base_history = dialog.to_ui_format()
            error_history = list(base_history)
            error_history.append({
                "role": MessageRole.ASSISTANT.value,
                "content": f"⚠️ Ошибка: {str(e)[:100]}"
            })
            yield (error_history, "", dialog_id)
    
    def _get_cached_history(self, cache_key: str, base_history: List[Dict]) -> List[Dict]:
        """
        Возвращает кэшированную копию базовой истории.
        Избегает полного копирования на каждом шаге.
        """
        if cache_key not in self._partial_update_cache:
            # Создаем shallow copy только один раз
            self._partial_update_cache[cache_key] = list(base_history)
        
        # Возвращаем копию кэша (только верхнего уровня)
        return list(self._partial_update_cache[cache_key])
    
    def _clear_cache(self, cache_key: str):
        """Очищает кэш для данного диалога"""
        if cache_key in self._partial_update_cache:
            del self._partial_update_cache[cache_key]