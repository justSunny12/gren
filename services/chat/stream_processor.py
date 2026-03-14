# services/chat/stream_processor.py
"""
Обработчик потока генерации ответа модели с кэшированием списка диалогов.
"""
import threading
from typing import AsyncGenerator, List, Dict, Optional, Tuple

from models.enums import MessageRole
from services.chat.operations import ChatOperations
from services.chat.naming_service import ChatNamingService
from services.chat.partial_cache import PartialUpdateCache
from services.chat.core import validate_message, sanitize_user_input
from services.chat.formatter import format_history_for_model
from services.chat.naming import is_default_name
from container import container
from datetime import datetime

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
        stop_event: Optional[threading.Event],
        search_enabled: bool = False,
    ) -> AsyncGenerator[Tuple[List[Dict], str, str, str, str], None]:
        """Основной метод обработки потока с поддержкой поиска и актуальной даты."""

        # Валидация сообщения
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

        # ЗАХВАТЫВАЕМ СНЭПШОТ СПИСКА ЧАТОВ ДО НАЧАЛА ГЕНЕРАЦИИ
        initial_chat_list = self._get_chat_list_data('today')

        # Стартовый JS (блокировка кнопок)
        js_start = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(true); }"
        yield base_history, "", dialog_id, initial_chat_list, js_start

        accumulated_response = ""
        suffix_on_stop = "...<генерация прервана пользователем>"

        try:
            messages_to_use = formatted_history
            search_cfg = self.config.get("search", {})
            status_cfg = search_cfg.get("status_messages", {})
            searched = False
            query = ""

            # Этап 1: анализ необходимости поиска (Pass 1)
            if search_enabled and search_cfg.get("enabled", False):
                deciding_text = status_cfg.get("deciding", "🔍 Анализирую запрос...")
                if deciding_text:
                    yield (
                        self._make_status_history(base_history, deciding_text),
                        deciding_text, dialog_id,
                        initial_chat_list,  # ← используем снэпшот
                        ""
                    )

                augmented, searched, query = await self._run_search(
                    prompt=prompt,
                    formatted_history=formatted_history,
                )

                if searched:
                    searching_tpl = status_cfg.get("searching", "🌐 Ищу в сети: {query}")
                    reading_text = status_cfg.get("reading", "📄 Читаю результаты...")
                    final_status = f"{searching_tpl.format(query=query)}\n{reading_text}"

                    yield (
                        self._make_status_history(base_history, final_status),
                        final_status, dialog_id,
                        initial_chat_list,  # ← снэпшот
                        ""
                    )
                    messages_to_use = augmented
                else:
                    self.logger.debug("➡️ Pass 1 решил не искать, продолжаем без поиска")
            else:
                self.logger.debug("➡️ Поиск отключён (search_enabled={} или search.enabled={})".format(
                    search_enabled, search_cfg.get("enabled")))

            # Этап 2: стриминг ответа модели
            async for batch in self.operations.stream_response(
                messages=messages_to_use,
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
                       initial_chat_list,  # ← снэпшот
                       "")

            was_stopped = stop_event and stop_event.is_set()
            final_text = accumulated_response + (suffix_on_stop if was_stopped else "")

            # Сохранение ответа в диалог
            self.operations.dialog_service.add_message(
                dialog_id,
                MessageRole.ASSISTANT,
                final_text
            )

            # Обновление контекста (оригинальный prompt, не augmented)
            try:
                dialog.add_interaction_to_context(prompt, final_text)
                dialog.save_context_state()
            except Exception as e:
                self.logger.warning("Ошибка при работе с контекстом: %s", e)

            # Финальная история
            updated_dialog = self.operations.dialog_service.get_dialog(dialog_id)
            final_history = updated_dialog.to_ui_format()

            # ФИНАЛЬНОЕ ОБНОВЛЕНИЕ СПИСКА ЧАТОВ
            final_chat_list = self._get_chat_list_data('today')
            js_stop = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield (final_history, final_text, dialog_id,
                   final_chat_list,  # ← свежий список
                   js_stop)

            # Генерация названия чата (если нужно)
            from services.chat.naming import is_default_name
            if is_default_name(updated_dialog.name, self.config) and len(updated_dialog.history) == 2:
                new_name = await self.naming_service.generate_name(prompt, final_text)
                if new_name:
                    updated_dialog.rename(new_name)
                    self.operations.dialog_service.storage.save_dialog(updated_dialog)
                    # ЕЩЁ ОДНО ФИНАЛЬНОЕ ОБНОВЛЕНИЕ ПОСЛЕ ПЕРЕИМЕНОВАНИЯ
                    renamed_chat_list = self._get_chat_list_data('today')
                    update_js = f"""
                    <script>
                    if (window.renderChatList) {{
                        window.renderChatList({renamed_chat_list}, 'today');
                    }}
                    </script>
                    """
                    yield (final_history, "", dialog_id, renamed_chat_list, update_js)

            self.cache.clear(cache_key)

        except Exception as e:
            self.logger.error("❌ Ошибка в process_message_stream: %s", e)
            self.cache.clear(cache_key)
            # Пытаемся получить актуальную историю диалога
            try:
                dialog = self.operations.dialog_service.get_dialog(dialog_id)
                base_history = dialog.to_ui_format() if dialog else []
            except:
                base_history = []
            error_history = list(base_history)
            error_history.append({
                "role": MessageRole.ASSISTANT.value,
                "content": f"⚠️ Ошибка: {str(e)[:100]}"
            })
            # В случае ошибки отдаём свежий список (на всякий случай)
            error_chat_list = self._get_chat_list_data('today')
            yield (error_history, "", dialog_id, error_chat_list, "")

    async def _run_search(
        self,
        prompt: str,
        formatted_history: List[Dict],
    ) -> Tuple[List[Dict], bool, str]:
        """
        Pass 1 + Tavily. Обычная async функция — никаких yield.

        Возвращает:
            augmented_messages  — история с инжектированным контекстом поиска
            searched            — был ли выполнен поиск
            query               — поисковый запрос (для отображения статуса)
        """
        try:
            search_manager = container.get("search_service")
        except Exception as e:
            self.logger.error("SearchManager недоступен: %s", e)
            return formatted_history, False, ""

        from services.search.manager import SearchOutcome
        outcome: SearchOutcome = await search_manager.process(
            user_prompt=prompt,
            original_messages=formatted_history,
        )

        if not outcome.searched:
            return formatted_history, False, ""

        return outcome.augmented_messages, True, outcome.query

    def _make_status_history(self, base_history: List[Dict], text: str) -> List[Dict]:
        """Добавляет временное сообщение-статус ассистента в историю для UI."""
        history = list(base_history)
        history.append({
            "role": MessageRole.ASSISTANT.value,
            "content": text,
        })
        return history

    def _get_chat_list_data(self, scroll_target: str = 'none') -> str:
        from handlers.chat_list import ChatListHandler
        return ChatListHandler().get_chat_list_data(scroll_target=scroll_target)