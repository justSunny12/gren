# handlers/message_handler.py
import threading
import time
from typing import AsyncGenerator, List, Optional, Tuple
from .base import BaseHandler
from services.user_config_service import user_config_service
from models.enums import MessageRole

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
        """Ленивое получение токенизатора из model_service (безопасно)"""
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
        """Безопасно подсчитывает количество токенов в промпте"""
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
        """
        Асинхронно стримит ответ модели, НЕ добавляя сообщение пользователя.
        Предполагается, что сообщение пользователя уже добавлено в диалог.
        """
        if not self._stream_lock.acquire(blocking=False):
            error_history = [{"role": MessageRole.ASSISTANT.value,
                            "content": "⚠️ Уже выполняется другая генерация. Подождите."}]
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield error_history, "", chat_id or "", self.get_chat_list_data(scroll_target='today'), js_code
            return

        try:
            dialog = self.dialog_service.get_dialog(chat_id)
            if not dialog:
                raise ValueError(f"Диалог {chat_id} не найден")

            # Получаем контекст (суммаризации и т.д.)
            context = dialog.get_context_for_generation()
            messages_for_model = []
            if context:
                messages_for_model.append({"role": "system", "content": context})
            messages_for_model.append({"role": "user", "content": prompt})

            user_config = user_config_service.get_user_config(force_reload=True)
            enable_thinking = user_config.generation.enable_thinking
            if enable_thinking is None:
                enable_thinking = False

            stop_event = threading.Event()
            self._active_stop_event = stop_event
            self._active_dialog_id = chat_id

            async for result in self.chat_service.process_message_stream(
                prompt=prompt,
                dialog_id=chat_id,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event,
                messages_for_model=messages_for_model
            ):
                yield result

        except Exception as e:
            print(f"❌ Ошибка в генерации: {e}")
            try:
                dialog = self.dialog_service.get_dialog(chat_id) if chat_id else None
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