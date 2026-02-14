# handlers/message_handler.py
import threading
import time
import re
from typing import AsyncGenerator, List, Optional, Tuple
from .base import BaseHandler
from services.user_config_service import user_config_service
from models.enums import MessageRole

def format_think_markdown(text: str) -> str:
    """
    Заменяет <think> на '<div class="thinking">', а </think> на '</div>' в потоке.
    Удаляет все переносы строк сразу после открывающего тега.
    """
    if not text:
        return text
    result = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith('<think>', i):
            result.append('<div class="thinking">')
            i += 7
            # Удаляем все последующие переносы строк
            while i < n and text[i] == '\n':
                i += 1
        elif text.startswith('</think>', i):
            result.append('</div>')
            i += 8
        else:
            result.append(text[i])
            i += 1
    return ''.join(result)


def clean_think_block(text: str) -> str:
    """
    Удаляет последний перенос строки перед закрывающим тегом </div> в блоке .thinking.
    Применяется после завершения генерации.
    """
    if not text:
        return text
    # Ищем блок .thinking, который заканчивается на \n</div>
    pattern = r'(<div class="thinking">.*?)\n(</div>)'
    return re.sub(pattern, r'\1\2', text, flags=re.DOTALL)


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
                model_service = container.get_model_service()
                self._tokenizer = model_service.get_tokenizer()
            except Exception as e:
                print(f"⚠️ Не удалось получить токенизатор: {e}")
                self._tokenizer = None
        return self._tokenizer

    def _get_prompt_token_count(self, messages: List[dict]) -> Optional[int]:
        try:
            if not self.tokenizer:
                return None
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            tokens = self.tokenizer.encode(prompt)
            return len(tokens)
        except Exception as e:
            print(f"⚠️ Ошибка подсчёта токенов: {e}")
            return None

    async def send_message_stream_handler(
        self,
        prompt: str,
        chat_id: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float]
    ) -> AsyncGenerator[Tuple[List[dict], str, str, str, str], None]:
        if not self._stream_lock.acquire(blocking=False):
            error_history = [{"role": MessageRole.ASSISTANT.value,
                            "content": "⚠️ Уже выполняется другая генерация. Подождите."}]
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield error_history, "", chat_id or "", self.get_chat_list_data(scroll_target='today'), js_code
            return

        try:
            stop_event = threading.Event()
            self._active_stop_event = stop_event
            self._active_dialog_id = chat_id

            user_config = user_config_service.get_user_config(force_reload=True)
            enable_thinking = user_config.generation.enable_thinking
            if enable_thinking is None:
                enable_thinking = False

            prompt_tokens = self._get_prompt_token_count([{"role": "user", "content": prompt}])
            start_time = time.time()
            first_token_received = False

            async for history, acc_text, dialog_id_out, chat_list_data, js_code in self.chat_service.process_message_stream(
                prompt=prompt,
                dialog_id=chat_id,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            ):
                # ===== ПРЕОБРАЗОВАНИЕ ТЕГОВ THINK В HTML-БЛОК =====
                if acc_text and history and history[-1].get('role') == MessageRole.ASSISTANT.value:
                    formatted = format_think_markdown(acc_text)
                    history[-1]['content'] = formatted
                # ===================================================

                if not first_token_received and history:
                    last_msg = history[-1]
                    if last_msg.get('role') == MessageRole.ASSISTANT.value and last_msg.get('content'):
                        if last_msg['content'].strip():
                            ttft = time.time() - start_time
                            token_info = f", контекст: {prompt_tokens} токенов" if prompt_tokens else ""
                            # print(f"⚡ TTFT: {ttft:.3f} сек{token_info}")
                            first_token_received = True

                yield history, "", dialog_id_out, chat_list_data, js_code

            # ===== СОХРАНЕНИЕ ПОСЛЕ ЗАВЕРШЕНИЯ СТРИМА =====
            if dialog_id_out:
                final_dialog = self.dialog_service.get_dialog(dialog_id_out)
                if final_dialog and final_dialog.history and final_dialog.history[-1].role == MessageRole.ASSISTANT:
                    original = final_dialog.history[-1].content
                    # Применяем основное форматирование (на случай, если что-то не применилось)
                    formatted = format_think_markdown(original)
                    # Удаляем конечный перенос перед закрывающим тегом
                    cleaned = clean_think_block(formatted)
                    if cleaned != original:
                        final_dialog.history[-1].content = cleaned
                        self.dialog_service.save_dialog(dialog_id_out)
                        # Отправляем обновлённую историю клиенту
                        updated_history = final_dialog.to_ui_format()
                        yield updated_history, "", dialog_id_out, chat_list_data, ""

        except Exception as e:
            print(f"❌ Ошибка в генерации: {e}")
            try:
                dialog = self.dialog_service.get_dialog(chat_id) if chat_id else None
                if dialog and dialog.history and dialog.history[-1].role == MessageRole.ASSISTANT:
                    original = dialog.history[-1].content
                    formatted = format_think_markdown(original)
                    cleaned = clean_think_block(formatted)
                    if cleaned != original:
                        dialog.history[-1].content = cleaned
                        self.dialog_service.save_dialog(chat_id)
                history = dialog.to_ui_format() if dialog else []
            except:
                history = []
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield history, "", chat_id or "", self.get_chat_list_data(scroll_target='today'), js_code
        finally:
            self._active_stop_event = None
            self._active_dialog_id = None
            self._stream_lock.release()

    def stop_active_generation(self) -> bool:
        if self._active_stop_event and not self._active_stop_event.is_set():
            self._active_stop_event.set()
            return True
        return False

    def get_chat_list_data(self, scroll_target: str = 'none'):
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data(scroll_target=scroll_target)
