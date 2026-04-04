# services/chat/stream_processor.py

import threading
import asyncio
from typing import AsyncGenerator, List, Dict, Optional, Tuple

from models.enums import MessageRole
from services.chat.operations import ChatOperations
from services.chat.naming_service import ChatNamingService
from services.chat.naming import is_default_name
from services.chat.partial_cache import PartialUpdateCache
from services.chat.core import validate_message, sanitize_user_input
from container import container


class MessageStreamProcessor:
    """Координирует потоковую обработку одного сообщения."""

    def __init__(self, config: dict, operations: ChatOperations):
        self.config = config
        self.operations = operations
        self.naming_service = ChatNamingService(config)
        self.cache = PartialUpdateCache()
        self._logger = None
        self._chat_list_handler = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = container.get_logger()
        return self._logger

    def _get_chat_list_data(self, scroll_target: str = 'none') -> str:
        if self._chat_list_handler is None:
            from handlers.chat_list import ChatListHandler
            self._chat_list_handler = ChatListHandler()
        return self._chat_list_handler.get_chat_list_data(scroll_target=scroll_target)

    def _make_status_history(self, base_history: List[Dict], text: str) -> List[Dict]:
        return list(base_history) + [{"role": MessageRole.ASSISTANT.value, "content": text}]

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
        is_valid, error = validate_message(prompt)
        if not is_valid:
            yield [], error, dialog_id or "", self._get_chat_list_data('today'), ""
            return

        prompt = sanitize_user_input(prompt)
        dialog = self.operations.dialog_service.get_dialog(dialog_id)
        if not dialog:
            yield [], "Диалог не найден", dialog_id, self._get_chat_list_data('today'), ""
            return

        context_str = dialog.get_context_for_generation()
        self.logger.debug(f"📚 Контекст для генерации: {len(context_str)} символов")

        messages = []
        if context_str:
            messages.append({"role": "system", "content": context_str})
        messages.append({"role": "user", "content": prompt})

        base_history = dialog.to_ui_format()
        cache_key = f"{dialog_id}_{len(base_history)}"
        # Снапшот списка чатов делается один раз — до начала генерации.
        # После финального yield повторная выборка не нужна: обновление сайдбара
        # (в т.ч. новое имя чата) произойдёт через background_tasks.
        initial_chat_list = self._get_chat_list_data('today')

        accumulated_response = ""
        suffix_on_stop = "...<генерация прервана пользователем>"

        try:
            messages_to_use = messages
            search_cfg = self.config.get("search", {})
            status_cfg = search_cfg.get("status_messages", {})

            if search_enabled and search_cfg.get("enabled", False):
                deciding_text = status_cfg.get("deciding", "🔍 Анализирую запрос...")
                if deciding_text:
                    yield (
                        self._make_status_history(base_history, deciding_text),
                        deciding_text, dialog_id, initial_chat_list, ""
                    )

                augmented, searched, query = await self._run_search(
                    prompt=prompt,
                    formatted_history=messages,
                )

                if searched:
                    searching_tpl = status_cfg.get("searching", "🌐 Ищу в сети: {query}")
                    reading_text = status_cfg.get("reading", "📄 Читаю результаты...")
                    final_status = f"{searching_tpl.format(query=query)}\n{reading_text}"
                    yield (
                        self._make_status_history(base_history, final_status),
                        final_status, dialog_id, initial_chat_list, ""
                    )
                    messages_to_use = augmented
                else:
                    self.logger.debug("➡️ Pass 1 решил не искать, продолжаем без поиска")
            else:
                self.logger.debug(
                    "➡️ Поиск отключён (search_enabled=%s или search.enabled=%s)",
                    search_enabled, search_cfg.get("enabled")
                )

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
                yield history_for_ui, accumulated_response, dialog_id, initial_chat_list, ""

            was_stopped = stop_event and stop_event.is_set()
            final_text = accumulated_response + (suffix_on_stop if was_stopped else "")

            # Сохраняем сообщение ассистента в историю (быстрая операция: append в jsonl)
            self.operations.dialog_service.add_message(dialog_id, MessageRole.ASSISTANT, final_text)

            updated_dialog = self.operations.dialog_service.get_dialog(dialog_id)
            final_history = updated_dialog.to_ui_format()
            js_stop = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"

            # ─── НЕМЕДЛЕННО отправляем финальный ответ клиенту ───────────────
            # initial_chat_list уже актуален: диалог стал видимым на шаге
            # save_and_show_user_message, поэтому повторная выборка с диска не нужна
            # и не должна блокировать доставку последнего батча.
            yield final_history, final_text, dialog_id, initial_chat_list, js_stop

            # ─── Все тяжёлые IO-операции идут в фон ──────────────────────────
            async def background_tasks():
                # 1. Обновление контекста
                try:
                    dialog = self.operations.dialog_service.get_dialog(dialog_id)
                    if dialog:
                        dialog.add_interaction_to_context(prompt, final_text)
                        dialog.save_context_state()
                except Exception as e:
                    self.logger.warning("Ошибка при работе с контекстом: %s", e)

                # 2. Генерация названия чата (только для первого обмена)
                if is_default_name(updated_dialog.name, self.config) and len(updated_dialog.history) == 2:
                    try:
                        new_name = await self.naming_service.generate_name(prompt, final_text)
                        if new_name:
                            updated_dialog.rename(new_name)
                            self.operations.dialog_service.storage.save_dialog(updated_dialog)
                            self.logger.info("Название чата изменено на: %s", new_name)
                    except Exception as e:
                        self.logger.error("Ошибка при генерации названия чата: %s", e, exc_info=True)

            asyncio.create_task(background_tasks())

            self.cache.clear(cache_key)

        except Exception as e:
            self.logger.error("❌ Ошибка в process_message_stream: %s", e)
            self.cache.clear(cache_key)
            try:
                dialog = self.operations.dialog_service.get_dialog(dialog_id)
                base_history = dialog.to_ui_format() if dialog else []
            except Exception:
                base_history = []
            error_history = list(base_history) + [{
                "role": MessageRole.ASSISTANT.value,
                "content": f"⚠️ Ошибка: {str(e)[:100]}"
            }]
            yield error_history, "", dialog_id, self._get_chat_list_data('today'), ""

    async def _run_search(
        self,
        prompt: str,
        formatted_history: List[Dict],
    ) -> Tuple[List[Dict], bool, str]:
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