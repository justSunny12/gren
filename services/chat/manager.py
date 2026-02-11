# services/chat/manager.py
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
    
    async def _generate_chat_name(
        self,
        dialog,
        user_message: str,
        assistant_message: str
    ) -> Optional[str]:
        """Асинхронно генерирует название чата через L1 суммаризатор."""
        try:
            config = self.operations.get_config()
            naming_config = config.get("chat_naming", {})
            if not naming_config.get("enabled", True):
                return None

            max_length = naming_config.get("max_name_length", 50)
            
            from services.context.summarizers import SummarizerFactory
            summarizers = SummarizerFactory.get_all_summarizers(
                config.get("context", {})
            )
            l1_summarizer = summarizers["l1"]

            interaction_text = (
                f"Пользователь: {user_message}\n"
                f"Ассистент: {assistant_message}"
            )

            system_prompt = naming_config.get(
                "system_prompt",
                "Ты создаёшь краткие названия для диалогов на основе первого обмена сообщениями. "
                "Название должно быть не длиннее 50 символов, отражать суть разговора, "
                "быть на языке пользователя. Ответ должен содержать только название, "
                "без дополнительного текста, кавычек или форматирования."
            )
            user_prompt = f"Диалог:\n{interaction_text}\n\nКраткое название:"

            result = await l1_summarizer.summarize(
                interaction_text,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=naming_config.get("max_tokens", 50),
                temperature=naming_config.get("temperature", 0.5),
                top_p=naming_config.get("top_p", 0.9),
                top_k=naming_config.get("top_k", 40),
                repetition_penalty=naming_config.get("repetition_penalty", 1.1)
            )

            if not result.success:
                print(f"⚠️ Не удалось сгенерировать название: {result.error}")
                return None

            name = result.summary.strip()
            if name.startswith("[L1 Summary]"):
                name = name.replace("[L1 Summary]", "", 1).strip()
            name = name.strip('"\'`').strip()
            if len(name) > max_length:
                name = name[:max_length-3] + "..."
            name = " ".join(name.splitlines())

            return name if name else None

        except Exception as e:
            print(f"❌ Ошибка в _generate_chat_name: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_chat_list_data(self) -> str:
        """Возвращает JSON с актуальным списком чатов."""
        from handlers.chat_list import ChatListHandler
        return ChatListHandler().get_chat_list_data()
    
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
        """
        Обрабатывает входящее сообщение и асинхронно стримит ответ с батчингом.
        Возвращает: (history, accumulated_text, dialog_id, chat_list_data, js_code)
        """
        from models.enums import MessageRole
        
        # 1. Валидация
        is_valid, error = validate_message(prompt)
        if not is_valid:
            yield [], error, dialog_id or "", self._get_chat_list_data(), ""
            return
        
        prompt = sanitize_user_input(prompt)
        
        # 2. Получаем диалог
        dialog = self.operations.dialog_service.get_dialog(dialog_id)
        if not dialog:
            yield [], "Диалог не найден", dialog_id, self._get_chat_list_data(), ""
            return
        
        # 3. Получаем конфигурацию
        config = self.operations.get_config()
        
        # 4. Форматируем историю для модели
        if messages_for_model is not None:
            formatted_history = messages_for_model
        else:
            formatted_history = format_history_for_model(dialog.history)
        
        # 5. Подготавливаем накопители
        accumulated_response = ""
        suffix_on_stop = "...<генерация прервана пользователем>"
        
        # 6. Кешируем базовую историю
        base_history = dialog.to_ui_format()
        cache_key = f"{dialog_id}_{len(base_history)}"
        
        # JS код для включения кнопок остановки
        js_start = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(true); }"
        yield base_history, "", dialog_id, self._get_chat_list_data(), js_start
        
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
                       self._get_chat_list_data(), "")
            
            # 8. После завершения стриминга
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
            
            # 12. Финальный yield – ответ уже полностью получен
            updated_dialog = self.operations.dialog_service.get_dialog(dialog_id)
            final_history = updated_dialog.to_ui_format()
            js_stop = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield (final_history, final_text, dialog_id,
                   self._get_chat_list_data(), js_stop)
            
            # 13. Асинхронная генерация названия (только для первого взаимодействия)
            if is_default_name(updated_dialog.name, config) and len(updated_dialog.history) == 2:
                new_name = await self._generate_chat_name(
                    updated_dialog,
                    prompt,
                    final_text
                )
                if new_name:
                    updated_dialog.rename(new_name)
                    self.operations.dialog_service.storage.save_dialog(updated_dialog)
                    
                    updated_chat_list = self._get_chat_list_data()
                    update_js = f"""
                    <script>
                    if (window.renderChatList) {{
                        window.renderChatList({updated_chat_list});
                    }}
                    </script>
                    """
                    yield (final_history, "", dialog_id, updated_chat_list, update_js)
            
            # 14. Очищаем кэш
            self._clear_cache(cache_key)
            
        except Exception as e:
            print(f"❌ Ошибка в process_message_stream: {e}")
            import traceback
            traceback.print_exc()
            self._clear_cache(cache_key)
            base_history = dialog.to_ui_format()
            error_history = list(base_history)
            error_history.append({
                "role": MessageRole.ASSISTANT.value,
                "content": f"⚠️ Ошибка: {str(e)[:100]}"
            })
            yield (error_history, "", dialog_id, self._get_chat_list_data(), "")
    
    def _get_cached_history(self, cache_key: str, base_history: List[Dict]) -> List[Dict]:
        if cache_key not in self._partial_update_cache:
            self._partial_update_cache[cache_key] = list(base_history)
        return list(self._partial_update_cache[cache_key])
    
    def _clear_cache(self, cache_key: str):
        if cache_key in self._partial_update_cache:
            del self._partial_update_cache[cache_key]