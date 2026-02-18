# services/chat/stream_processor.py
"""
Обработчик потока генерации ответа модели.
"""
import threading
import traceback
from typing import AsyncGenerator, List, Dict, Optional, Tuple

from models.enums import MessageRole
from services.chat.operations import ChatOperations
from services.chat.naming_service import ChatNamingService
from services.chat.partial_cache import PartialUpdateCache
from services.chat.core import validate_message, sanitize_user_input
from services.chat.formatter import format_history_for_model
from services.chat.naming import is_default_name
from container import container


class MessageStreamProcessor:
    """Координирует потоковую обработку одного сообщения."""

    def __init__(self, config: dict, operations: ChatOperations):
        self.config = config
        self.operations = operations
        self.naming_service = ChatNamingService(config)
        self.cache = PartialUpdateCache()
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    async def process(
        self,
        prompt: str,
        dialog_id: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        enable_thinking: Optional[bool],
        stop_event: Optional[threading.Event]
    ) -> AsyncGenerator[Tuple[List[Dict], str, str, str, str], None]:
        """Основной метод обработки потока."""
        # Валидация
        is_valid, error = validate_message(prompt)
        if not is_valid:
            yield [], error, dialog_id or "", self._get_chat_list_data('today'), ""
            return

        prompt = sanitize_user_input(prompt)
        dialog = self.operations.dialog_service.get_dialog(dialog_id)
        if not dialog:
            yield [], "Диалог не найден", dialog_id, self._get_chat_list_data('today'), ""
            return

        # Подготовка истории
        formatted_history = format_history_for_model(dialog.history)
        base_history = dialog.to_ui_format()
        cache_key = f"{dialog_id}_{len(base_history)}"

        js_start = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(true); }"
        yield base_history, "", dialog_id, self._get_chat_list_data('today'), js_start

        accumulated_response = ""
        suffix_on_stop = "...<генерация прервана пользователем>"

        try:
            # Стриминг ответа
            async for batch in self.operations.stream_response(
                messages=formatted_history,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            ):
                accumulated_response += batch
                history_for_ui = self.cache.get(cache_key, base_history)
                history_for_ui.append({
                    "role": MessageRole.ASSISTANT.value,
                    "content": accumulated_response
                })
                yield (history_for_ui, accumulated_response, dialog_id,
                       self._get_chat_list_data('today'), "")

            was_stopped = stop_event and stop_event.is_set()
            final_text = accumulated_response + (suffix_on_stop if was_stopped else "")

            # Сохранение в диалог
            self.operations.dialog_service.add_message(
                dialog_id,
                MessageRole.ASSISTANT,
                final_text
            )

            # Обновление контекста
            try:
                dialog.add_interaction_to_context(prompt, final_text)
                dialog.save_context_state()
            except Exception as e:
                self.logger.warning("Ошибка при работе с контекстом: %s", e)

            # Финальная история
            updated_dialog = self.operations.dialog_service.get_dialog(dialog_id)
            final_history = updated_dialog.to_ui_format()
            js_stop = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield (final_history, final_text, dialog_id,
                   self._get_chat_list_data('today'), js_stop)

            # Генерация названия (если нужно)
            if is_default_name(updated_dialog.name, self.config) and len(updated_dialog.history) == 2:
                new_name = await self.naming_service.generate_name(prompt, final_text)
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

            self.cache.clear(cache_key)

        except Exception as e:
            self.logger.exception("Ошибка в process_message_stream: %s", e)
            self.cache.clear(cache_key)
            base_history = dialog.to_ui_format()
            error_history = list(base_history)
            error_history.append({
                "role": MessageRole.ASSISTANT.value,
                "content": f"⚠️ Ошибка: {str(e)[:100]}"
            })
            yield (error_history, "", dialog_id, self._get_chat_list_data('today'), "")

    def _get_chat_list_data(self, scroll_target: str = 'none') -> str:
        from handlers.chat_list import ChatListHandler
        return ChatListHandler().get_chat_list_data(scroll_target=scroll_target)