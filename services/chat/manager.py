# services/chat/manager.py
import asyncio
import threading
import traceback
import re
from typing import AsyncGenerator, List, Dict, Optional, Tuple, Any

from .core import validate_message, sanitize_user_input
from .formatter import format_history_for_model
from .naming import is_default_name
from .operations import ChatOperations


class ChatManager:
    """Главный менеджер для работы с чатом"""
    
    def __init__(self):
        self.operations = ChatOperations()
        self._partial_update_cache = {}
    
    async def _generate_chat_name(
        self,
        dialog,
        user_message: str,
        assistant_message: str
    ) -> Optional[str]:
        # ... (без изменений, скролл не затрагивает)
        pass
    
    def _get_chat_list_data(self, scroll_target: str = 'none') -> str:
        from handlers.chat_list import ChatListHandler
        return ChatListHandler().get_chat_list_data(scroll_target=scroll_target)
    
    async def process_message_stream(
        self,
        prompt: str,
        dialog_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        stop_event: Optional[threading.Event] = None,
        messages_for_model: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[Tuple[List[Dict], str, str, str, str], None]:
        from models.enums import MessageRole
        
        is_valid, error = validate_message(prompt)
        if not is_valid:
            yield [], error, dialog_id or "", self._get_chat_list_data('today'), ""
            return
        
        prompt = sanitize_user_input(prompt)
        dialog = self.operations.dialog_service.get_dialog(dialog_id)
        if not dialog:
            yield [], "Диалог не найден", dialog_id, self._get_chat_list_data('today'), ""
            return
        
        config = self.operations.get_config()
        
        if messages_for_model is not None:
            formatted_history = messages_for_model
        else:
            formatted_history = format_history_for_model(dialog.history)
        
        accumulated_response = ""
        suffix_on_stop = "...<генерация прервана пользователем>"
        
        base_history = dialog.to_ui_format()
        cache_key = f"{dialog_id}_{len(base_history)}"
        
        js_start = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(true); }"
        yield base_history, "", dialog_id, self._get_chat_list_data('today'), js_start
        
        try:
            async for batch in self.operations.stream_response(
                messages=formatted_history,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            ):
                accumulated_response += batch
                history_for_ui = self._get_cached_history(cache_key, base_history)
                history_for_ui.append({
                    "role": MessageRole.ASSISTANT.value,
                    "content": accumulated_response
                })
                yield (history_for_ui, accumulated_response, dialog_id,
                       self._get_chat_list_data('today'), "")
            
            was_stopped = stop_event and stop_event.is_set()
            final_text = accumulated_response
            if was_stopped:
                final_text += suffix_on_stop
            
            self.operations.dialog_service.add_message(
                dialog_id,
                MessageRole.ASSISTANT,
                final_text
            )
            
            try:
                dialog.add_interaction_to_context(prompt, final_text)
            except Exception as e:
                print(f"⚠️ Ошибка при добавлении взаимодействия в контекст: {e}")
            
            try:
                dialog.save_context_state()
            except Exception as e:
                print(f"⚠️ Ошибка при сохранении состояния контекста: {e}")
            
            updated_dialog = self.operations.dialog_service.get_dialog(dialog_id)
            final_history = updated_dialog.to_ui_format()
            js_stop = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield (final_history, final_text, dialog_id,
                   self._get_chat_list_data('today'), js_stop)
            
            if is_default_name(updated_dialog.name, config) and len(updated_dialog.history) == 2:
                new_name = await self._generate_chat_name(
                    updated_dialog,
                    prompt,
                    final_text
                )
                if new_name:
                    updated_dialog.rename(new_name)
                    self.operations.dialog_service.storage.save_dialog(updated_dialog)
                    updated_chat_list = self._get_chat_list_data('today')
                    update_js = f"""
                    <script>
                    if (window.renderChatList) {{
                        window.renderChatList({updated_chat_list}, 'today');
                    }}
                    </script>
                    """
                    yield (final_history, "", dialog_id, updated_chat_list, update_js)
            
            self._clear_cache(cache_key)
            
        except Exception as e:
            print(f"❌ Ошибка в process_message_stream: {e}")
            traceback.print_exc()
            self._clear_cache(cache_key)
            base_history = dialog.to_ui_format()
            error_history = list(base_history)
            error_history.append({
                "role": MessageRole.ASSISTANT.value,
                "content": f"⚠️ Ошибка: {str(e)[:100]}"
            })
            yield (error_history, "", dialog_id, self._get_chat_list_data('today'), "")
    
    def _get_cached_history(self, cache_key: str, base_history: List[Dict]) -> List[Dict]:
        if cache_key not in self._partial_update_cache:
            self._partial_update_cache[cache_key] = list(base_history)
        return list(self._partial_update_cache[cache_key])
    
    def _clear_cache(self, cache_key: str):
        if cache_key in self._partial_update_cache:
            del self._partial_update_cache[cache_key]