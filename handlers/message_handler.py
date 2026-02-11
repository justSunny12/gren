# handlers/message_handler.py (исправленная версия)
import threading
from typing import AsyncGenerator, List, Optional, Tuple, Dict, Any
from .base import BaseHandler

class MessageHandler(BaseHandler):
    """Обработчик сообщений с поддержкой асинхронного стриминга"""
    
    def __init__(self):
        super().__init__()
        self._active_stop_event = None
        self._active_dialog_id = None
        self._stream_lock = threading.Lock()
        self._chat_service = None
    
    @property
    def chat_service(self):
        if self._chat_service is None:
            from container import container
            self._chat_service = container.get_chat_service()
        return self._chat_service
    
    async def send_message_stream_handler(
        self,
        prompt: str,
        chat_id: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        enable_thinking: Optional[bool]
    ) -> AsyncGenerator[Tuple[List[Dict], str, str, str, str], None]:
        """Асинхронный обработчик для потоковой генерации с JS триггером"""
        from models.enums import MessageRole
                
        if not self._stream_lock.acquire(blocking=False):
            error_history = [{"role": MessageRole.ASSISTANT.value,
                            "content": "⚠️ Уже выполняется другая генерация. Подождите."}]
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield error_history, "", chat_id or "", self.get_chat_list_data(), js_code
            return
                
        try:
            if not chat_id:
                chat_id = self.dialog_service.create_dialog()
            
            self.dialog_service.add_message(chat_id, MessageRole.USER, prompt)
            
            dialog = self.dialog_service.get_dialog(chat_id)
            if not dialog:
                raise ValueError(f"Диалог {chat_id} не найден после добавления сообщения")
            
            history_with_user_message = list(dialog.to_ui_format())
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(true); }"
            yield history_with_user_message, "", chat_id, self.get_chat_list_data(), js_code
            
            stop_event = threading.Event()
            self._active_stop_event = stop_event
            self._active_dialog_id = chat_id
            
            context = dialog.get_context_for_generation()
            messages_for_model = []
            if context:
                messages_for_model.append({
                    "role": "system",
                    "content": context
                })
            for msg in dialog.history:
                messages_for_model.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            
            # Пробрасываем результаты из ChatManager без изменений
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
            import traceback
            traceback.print_exc()
            try:
                dialog = self.dialog_service.get_dialog(chat_id) if chat_id else None
                history = dialog.to_ui_format() if dialog else []
            except:
                history = []
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield history, "", chat_id or "", self.get_chat_list_data(), js_code
            
        finally:
            self._active_stop_event = None
            self._active_dialog_id = None
            self._stream_lock.release()
    
    def stop_active_generation(self) -> bool:
        if self._active_stop_event and not self._active_stop_event.is_set():
            self._active_stop_event.set()
            return True
        return False
    
    def get_chat_list_data(self):
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data()