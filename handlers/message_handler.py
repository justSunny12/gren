# handlers/message_handler.py
import asyncio
import threading
import time
from typing import AsyncGenerator, List, Optional, Tuple

from .base import BaseHandler
from services.user_config_service import user_config_service
from models.enums import MessageRole
from services.model.thinking_handler import ThinkingHandler


class MessageHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self._active_stop_event = None
        self._active_dialog_id = None
        self._stream_lock = threading.Lock()
        self._chat_service = None
        self._tokenizer = None

    @property
    def chat_service(self):
        if self._chat_service is None:
            from container import container
            self._chat_service = container.get_chat_service()
        return self._chat_service

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            try:
                from container import container
                self._tokenizer = container.get_model_service().get_tokenizer()
            except Exception as e:
                self.logger.warning("⚠️ Не удалось получить токенизатор: %s", e)
        return self._tokenizer

    # ──────────────────────────────────────────────
    # Приватные хелперы
    # ──────────────────────────────────────────────

    def _normalize_and_save(self, dialog_id: str, thinking_seconds: float = None,
                            thinking_stopped: bool = False) -> Optional[List[dict]]:
        """
        Нормализует последнее сообщение ассистента для хранения.
        Перезаписывает последнюю строку history_*.jsonl с обновлённым контентом.
        Возвращает обновлённый UI-формат если контент изменился, иначе None.
        """
        dialog = self.dialog_service.get_dialog(dialog_id)
        if not (dialog and dialog.history and dialog.history[-1].role == MessageRole.ASSISTANT):
            return None

        msg = dialog.history[-1]
        normalized = ThinkingHandler.normalize_for_storage(
            msg.content, thinking_seconds, stopped=thinking_stopped
        )
        if normalized == msg.content:
            return None

        msg.content = normalized
        self.dialog_service.storage.rewrite_last_message(dialog)
        return dialog.to_ui_format()

    async def _log_generation_speed_async(self, dialog_id: str, start_time: float) -> None:
        """Логирует скорость генерации асинхронно (tokenizer.encode в thread pool)."""
        dialog = self.dialog_service.get_dialog(dialog_id)
        if not (dialog and dialog.history and dialog.history[-1].role == MessageRole.ASSISTANT):
            return

        final_text = dialog.history[-1].content
        elapsed = time.time() - start_time
        if elapsed <= 0:
            return

        try:
            if self.tokenizer:
                # tokenizer.encode — CPU-bound; запускаем в thread pool чтобы
                # не блокировать event loop и дать asyncio отправить последний
                # SSE-батч в браузер до начала тяжёлых вычислений.
                num_tokens = await asyncio.to_thread(self.tokenizer.encode, final_text)
                num_tokens = len(num_tokens)
                self.logger.stats(
                    "⚡ Скорость генерации: %.2f токенов/сек (%d токенов за %.2f сек)",
                    num_tokens / elapsed, num_tokens, elapsed,
                )
            else:
                est_tokens = len(final_text) // 4
                self.logger.stats(
                    "⚡ Скорость генерации (оценочно): %.2f токенов/сек (~%d токенов за %.2f сек)",
                    est_tokens / elapsed, est_tokens, elapsed,
                )
        except Exception as e:
            self.logger.warning("Не удалось подсчитать токены: %s", e)

    # ──────────────────────────────────────────────
    # Основной обработчик
    # ──────────────────────────────────────────────

    async def send_message_stream_handler(
        self,
        prompt: str,
        chat_id: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        search_enabled: Optional[bool] = None,
    ) -> AsyncGenerator[Tuple[List[dict], str, str, str, str], None]:

        if not self._stream_lock.acquire(blocking=False):
            js_stop = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield (
                [{"role": MessageRole.ASSISTANT.value,
                  "content": "⚠️ Уже выполняется другая генерация. Подождите."}],
                "", chat_id or "", self.get_chat_list_data(scroll_target='today'), js_stop,
            )
            return

        try:
            stop_event = threading.Event()
            self._active_stop_event = stop_event
            self._active_dialog_id = chat_id

            user_config = user_config_service.get_user_config()
            enable_thinking = user_config.generation.enable_thinking or False
            search_enabled = user_config.search_enabled or False

            dialog = self.dialog_service.get_dialog(chat_id) if chat_id else None
            total_context_chars = len(dialog.get_context_for_generation()) if dialog else 0

            start_time = time.time()
            first_token_received = False
            thinking_start_time: Optional[float] = None
            thinking_seconds: Optional[float] = None
            thinking_stopped: bool = False
            final_dialog_id = final_chat_list_data = None

            async for history, acc_text, dialog_id_out, chat_list_data, js_code in (
                self.chat_service.process_message_stream(
                    prompt=prompt,
                    dialog_id=chat_id,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    enable_thinking=enable_thinking,
                    stop_event=stop_event,
                    search_enabled=search_enabled,
                )
            ):
                # Форматирование блока размышлений на лету
                if enable_thinking and acc_text and history and \
                        history[-1].get('role') == MessageRole.ASSISTANT.value:

                    if thinking_start_time is None:
                        thinking_start_time = time.time()

                    if thinking_seconds is None and '</think>' in acc_text:
                        thinking_seconds = time.time() - thinking_start_time
                        self.logger.stats(
                            "💭 Блок размышлений завершен за %.2f секунд", thinking_seconds
                        )

                    if not thinking_stopped and stop_event.is_set() and thinking_seconds is None:
                        thinking_stopped = True

                    history[-1]['content'] = ThinkingHandler.format_stream_chunk(
                        acc_text, thinking_seconds, stopped=thinking_stopped
                    )

                if not first_token_received and history:
                    last = history[-1]
                    if last.get('role') == MessageRole.ASSISTANT.value \
                            and last.get('content', '').strip():
                        self.logger.stats(
                            "⚡ TTFT: %.3f сек, контекст: %d символов",
                            time.time() - start_time, total_context_chars,
                        )
                        first_token_received = True

                final_dialog_id, final_chat_list_data = dialog_id_out, chat_list_data
                yield history, "", dialog_id_out, chat_list_data, js_code

            # ── После завершения стрима ────────────────────────────────────────
            # КРИТИЧНО: сначала даём event loop отправить последний SSE-батч
            # в браузер, и только потом запускаем тяжёлые операции.
            # Без этого sleep(0) tokenizer.encode() блокирует event loop и браузер
            # получает последний батч с задержкой (буфер asyncio не флашится пока
            # event loop занят).
            await asyncio.sleep(0)

            if final_dialog_id:
                # Логируем скорость асинхронно (tokenizer в thread pool)
                await self._log_generation_speed_async(final_dialog_id, start_time)
                # _normalize_and_save — no-op для non-thinking, disk IO для thinking
                updated = self._normalize_and_save(final_dialog_id, thinking_seconds, thinking_stopped)
                if updated:
                    yield updated, "", final_dialog_id, final_chat_list_data, ""

        except Exception as e:
            self.logger.error("❌ Ошибка в генерации: %s", e)
            history = []
            try:
                if chat_id:
                    self._normalize_and_save(chat_id)
                    dialog = self.dialog_service.get_dialog(chat_id)
                    history = dialog.to_ui_format() if dialog else []
            except Exception as inner_e:
                self.logger.error("Ошибка при восстановлении после сбоя: %s", inner_e)
            js_stop = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield history, "", chat_id or "", self.get_chat_list_data(scroll_target='today'), js_stop

        finally:
            self._active_stop_event = None
            self._active_dialog_id = None
            self._stream_lock.release()

    def stop_active_generation(self) -> bool:
        if self._active_stop_event and not self._active_stop_event.is_set():
            self._active_stop_event.set()
            return True
        return False