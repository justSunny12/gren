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
    ) -> AsyncGenerator[Tuple[List[Dict], str, str, str, str], None]:
        """Асинхронный обработчик для потоковой генерации с JS триггером"""
        from models.enums import MessageRole
        
        # 1. Захватываем блокировку
        if not self._stream_lock.acquire(blocking=False):
            error_history = [{"role": MessageRole.ASSISTANT.value, 
                            "content": "⚠️ Уже выполняется другая генерация. Подождите."}]
            # При ошибке тоже отправляем JS код для переключения кнопок
            js_code = """
            <script>
            if (window.toggleGenerationButtons) {
                window.toggleGenerationButtons(false);
            }
            </script>
            """
            yield error_history, "", chat_id or "", self.get_chat_list_data(), js_code
            return
        
        try:
            # 2. Создаем событие для остановки
            stop_event = threading.Event()
            self._active_stop_event = stop_event
            self._active_dialog_id = chat_id
            
            # 3. Получаем поток от ChatManager
            stream_generator = self.chat_service.process_message_stream(
                prompt=prompt,
                dialog_id=chat_id,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking,
                stop_event=stop_event
            )
            
            # 4. Итерируем и добавляем chat_list_data
            last_yield_data = None
            async for history, accumulated_text, current_dialog_id in stream_generator:
                chat_list_data = self.get_chat_list_data()
                # Сохраняем последние данные для финального yield
                last_yield_data = (history, "", current_dialog_id, chat_list_data)
                # Промежуточные yield без JS кода
                yield history, "", current_dialog_id, chat_list_data, ""
            
            # 5. После завершения цикла (генерация завершена естественным путем)
            if last_yield_data:
                history, _, current_dialog_id, chat_list_data = last_yield_data
                # Добавляем JS код для переключения кнопок
                js_code = """
                <script>
                if (window.toggleGenerationButtons) {
                    window.toggleGenerationButtons(false);
                }
                </script>
                """
                yield history, "", current_dialog_id, chat_list_data, js_code
            else:
                # Если не было ни одного yield, отправляем пустой результат с JS кодом
                js_code = """
                <script>
                if (window.toggleGenerationButtons) {
                    window.toggleGenerationButtons(false);
                }
                </script>
                """
                yield [], "", chat_id or "", self.get_chat_list_data(), js_code
            
        except Exception as e:
            print(f"❌ Ошибка в send_message_stream_handler: {e}")
            import traceback
            traceback.print_exc()
            
            error_history = [{"role": MessageRole.ASSISTANT.value, 
                            "content": f"⚠️ Ошибка генерации: {str(e)[:100]}"}]
            # При ошибке тоже отправляем JS код для переключения кнопок
            js_code = """
            <script>
            if (window.toggleGenerationButtons) {
                window.toggleGenerationButtons(false);
            }
            </script>
            """
            yield error_history, "", chat_id or "", self.get_chat_list_data(), js_code
            
        finally:
            self._active_stop_event = None
            self._active_dialog_id = None
            self._stream_lock.release()
    
    def stop_active_generation(self) -> bool:
        """Останавливает активную генерацию. Вызывается из UI по нажатию кнопки 'Стоп'."""
        if self._active_stop_event and not self._active_stop_event.is_set():
            # print("[MessageHandler] Останавливаю активную генерацию...")
            self._active_stop_event.set()
            
            # Также возвращаем JS код для немедленного переключения кнопок
            # (хотя это будет обработано в stop_btn.click)
            return True
        return False
    
    def get_chat_list_data(self):
        """Получает данные списка чатов"""
        from .chat_list import ChatListHandler
        handler = ChatListHandler()
        return handler.get_chat_list_data()