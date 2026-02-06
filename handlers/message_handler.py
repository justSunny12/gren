# handlers/message_handler.py
# ЗАМЕНИТЕ ВЕСЬ СОДЕРЖИМЫЙ ФАЙЛ на код ниже:

import threading
from typing import AsyncGenerator, List, Optional, Tuple, Dict, Any
from .base import BaseHandler

class MessageHandler(BaseHandler):
    """Обработчик сообщений с поддержкой асинхронного стриминга"""
    
    def __init__(self):
        super().__init__()
        self._active_stop_event = None  # threading.Event для активной генерации
        self._active_dialog_id = None   # ID диалога, в котором идет генерация
        self._stream_lock = threading.Lock()  # Защита состояния
    
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
                
        # 1. Захватываем блокировку
        if not self._stream_lock.acquire(blocking=False):
            error_history = [{"role": MessageRole.ASSISTANT.value, 
                            "content": "⚠️ Уже выполняется другая генерация. Подождите."}]
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield error_history, "", chat_id or "", self.get_chat_list_data(), js_code
            return
                
        try:
            # 2. ДОБАВЛЯЕМ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ НЕМЕДЛЕННО
            
            # Если нет chat_id, создаем новый диалог
            if not chat_id:
                chat_id = self.dialog_service.create_dialog()
            
            # Добавляем сообщение пользователя в диалог
            self.dialog_service.add_message(chat_id, MessageRole.USER, prompt)
            
            # Получаем обновленный диалог с сообщением пользователя
            dialog = self.dialog_service.get_dialog(chat_id)
            if not dialog:
                raise ValueError(f"Диалог {chat_id} не найден после добавления сообщения")
            
            # Форматируем историю для UI (включая сообщение пользователя)
            from services.chat.formatter import format_history_for_ui
            history_with_user_message = format_history_for_ui(dialog.history)
                        
            # 3. НЕМЕДЛЕННО отправляем историю с сообщением пользователя
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(true); }"
            
            # ВОТ ОН - КРИТИЧЕСКИЙ YIELD! Отправляем историю СРАЗУ
            yield history_with_user_message, "", chat_id, self.get_chat_list_data(), js_code
            
            # 4. Создаем событие для остановки
            stop_event = threading.Event()
            self._active_stop_event = stop_event
            self._active_dialog_id = chat_id
            
            # 5. Получаем поток от ChatManager (БЕЗ повторного добавления сообщения пользователя)            
            # Форматируем историю для модели (уже содержит сообщение пользователя)
            from services.chat.formatter import format_history_for_model
            messages_for_model = format_history_for_model(dialog.history)
            
            # Получаем генератор стриминга ОТВЕТА (без сообщения пользователя)
            async for history, accumulated_text, current_dialog_id in self.chat_service.stream_response_only(
                messages=messages_for_model,
                dialog_id=chat_id,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            ):
                chat_list_data = self.get_chat_list_data()
                # Промежуточные yield без JS кода
                yield history, "", current_dialog_id, chat_list_data, ""
            
            # 6. После завершения стриминга
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            
            # Получаем финальный диалог
            final_dialog = self.dialog_service.get_dialog(chat_id)
            if final_dialog:
                final_history = format_history_for_ui(final_dialog.history)
                yield final_history, "", chat_id, self.get_chat_list_data(), js_code
            else:
                yield history_with_user_message, "", chat_id, self.get_chat_list_data(), js_code
                            
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            # При ошибке пытаемся вернуть историю с сообщением пользователя
            try:
                dialog = self.dialog_service.get_dialog(chat_id) if chat_id else None
                if dialog:
                    from services.chat.formatter import format_history_for_ui
                    history = format_history_for_ui(dialog.history)
                else:
                    history = []
            except:
                history = []
                
            js_code = "if (window.toggleGenerationButtons) { window.toggleGenerationButtons(false); }"
            yield history, "", chat_id or "", self.get_chat_list_data(), js_code
            
        finally:
            self._active_stop_event = None
            self._active_dialog_id = None
            self._stream_lock.release()
    
    def stop_active_generation(self) -> bool:
        """Останавливает активную генерацию. Вызывается из UI по нажатию кнопки 'Стоп'."""
        if self._active_stop_event and not self._active_stop_event.is_set():
            self._active_stop_event.set()
            
            return True
        return False
    
    def get_chat_list_data(self):
        """Получает данные списка чатов"""
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data()