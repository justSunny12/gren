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
    
    def send_message_handler(self, prompt, chat_id, max_tokens, temperature, enable_thinking):
        """Синхронный обработчик для обратной совместимости (оставляем как есть)."""
        try:
            if not prompt.strip():
                return [], "", chat_id or "", self.get_chat_list_data()

            if not chat_id:
                chat_id = self.dialog_service.create_dialog()

            history, _, new_chat_id = self.chat_service.process_message(
                prompt, chat_id, max_tokens, temperature, enable_thinking
            )

            chat_list_data = self.get_chat_list_data()
            return history, "", new_chat_id, chat_list_data

        except Exception as e:
            print(f"❌ Ошибка в send_message_handler: {e}")
            return [], "", chat_id or "", self.get_chat_list_data()
    
    async def send_message_stream_handler(
        self,
        prompt: str,
        chat_id: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        enable_thinking: Optional[bool]
    ) -> AsyncGenerator[Tuple[List[Dict], str, str, str], None]:
        """Асинхронный обработчик для потоковой генерации (вариант B).
        
        Yields:
            Кортеж (history, "", dialog_id, chat_list_data):
            - history: полная история для UI, где последнее сообщение ассистента нарастает
            - "": пустая строка (заглушка для обратной совместимости)
            - dialog_id: ID текущего диалога
            - chat_list_data: JSON строка с актуальным списком чатов
        """
        from models.enums import MessageRole
        
        # 1. Захватываем блокировку для защиты состояния
        if not self._stream_lock.acquire(blocking=False):
            # Если уже идет стриминг, возвращаем ошибку через yield
            error_history = [{"role": MessageRole.ASSISTANT.value, 
                              "content": "⚠️ Уже выполняется другая генерация. Подождите."}]
            yield error_history, "", chat_id or "", self.get_chat_list_data()
            return
        
        try:
            # 2. Создаем событие для остановки
            stop_event = threading.Event()
            self._active_stop_event = stop_event
            self._active_dialog_id = chat_id
            
            # 3. Запускаем потоковую генерацию через ChatManager
            async for history, accumulated_text, current_dialog_id in self.chat_service.process_message_stream(
                prompt=prompt,
                dialog_id=chat_id,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            ):
                # 4. Форматируем ответ в нужном для UI формате
                # history уже содержит нарастающий ответ ассистента (формат B)
                chat_list_data = self.get_chat_list_data()
                yield history, "", current_dialog_id, chat_list_data
                
            # 5. Финальный yield после завершения
            final_chat_list_data = self.get_chat_list_data()
            yield history, "", current_dialog_id, final_chat_list_data
            
        except Exception as e:
            print(f"❌ Критическая ошибка в send_message_stream_handler: {e}")
            import traceback
            traceback.print_exc()
            
            # Возвращаем историю с ошибкой
            error_history = [{"role": MessageRole.ASSISTANT.value, 
                              "content": f"⚠️ Ошибка генерации: {str(e)[:100]}"}]
            yield error_history, "", chat_id or "", self.get_chat_list_data()
            
        finally:
            # 6. Очищаем состояние
            self._active_stop_event = None
            self._active_dialog_id = None
            self._stream_lock.release()
    
    def stop_active_generation(self) -> bool:
        """Останавливает активную генерацию. Вызывается из UI по нажатию кнопки 'Стоп'."""
        if self._active_stop_event and not self._active_stop_event.is_set():
            print("[MessageHandler] Останавливаю активную генерацию...")
            self._active_stop_event.set()
            return True
        return False
    
    def get_chat_list_data(self):
        """Получает данные списка чатов"""
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data()