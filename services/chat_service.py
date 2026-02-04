# /services/chat_service.py
import re
import time
import traceback
from typing import Tuple, List, Dict, Any, Optional
from models.enums import MessageRole

class ChatService:
    """Сервис для логики чата"""

    def __init__(self):
        from container import container
        self.config = container.get_config()
        self.dialog_service = container.get_dialog_service()
        self.model_service = container.get_model_service()

    def process_message(self, prompt: str, dialog_id: Optional[str] = None,
                        max_tokens: Optional[int] = None,
                        temperature: Optional[float] = None,
                        enable_thinking: Optional[bool] = None) -> Tuple[List[Dict], str, str]:
        """Обрабатывает входящее сообщение"""
        try:
            if not prompt or not prompt.strip():
                return [], "⚠️ Введите сообщение", dialog_id or ""

            # Получаем или создаем диалог
            if not dialog_id:
                dialog_id = self.dialog_service.create_dialog()
                is_new_chat = True
            else:
                is_new_chat = False

            dialog_before = self.dialog_service.get_dialog(dialog_id)
            if not dialog_before:
                return [], "Ошибка: диалог не найден", dialog_id

            # Форматируем историю
            formatted_history = []
            for msg in dialog_before.history:
                formatted_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

            formatted_history.append({"role": "user", "content": prompt.strip()})

            # Генерируем ответ с помощью обновленного model_service
            response_text = ""
            if hasattr(self.model_service, 'generate_response'):
                start_time = time.time()
                response_text = self.model_service.generate_response(
                    messages=formatted_history,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    enable_thinking=enable_thinking
                )
            else:
                response_text = "Ошибка: сервис модели не поддерживается"

            # Добавляем сообщения в диалог
            self.dialog_service.add_message(dialog_id, MessageRole.USER, prompt)
            self.dialog_service.add_message(dialog_id, MessageRole.ASSISTANT, response_text)

            # Переименовываем чат при первом сообщении или стандартном названии
            if is_new_chat or "Новый чат" in dialog_before.name:
                self._generate_chat_name_simple(dialog_id, prompt)

            # Получаем финальный диалог
            final_dialog = self.dialog_service.get_dialog(dialog_id)
            display_history = final_dialog.to_ui_format()

            return display_history, "", dialog_id

        except Exception as e:
            print(f"❌ Ошибка в process_message: {e}")
            traceback.print_exc()
            return [], f"⚠️ Ошибка: {str(e)[:100]}", dialog_id or ""

    # Метод _generate_chat_name_simple остаётся без изменений
    def _generate_chat_name_simple(self, dialog_id: str, prompt: str):
        # ... (оставляем существующий код)
        pass

    def get_chat_history(self, dialog_id: Optional[str] = None) -> List[Dict]:
        """Получает историю чата"""
        try:
            if not dialog_id:
                dialog = self.dialog_service.get_current_dialog()
            else:
                dialog = self.dialog_service.get_dialog(dialog_id)

            if dialog:
                return dialog.to_ui_format()
            return []
        except Exception:
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику генерации"""
        try:
            if hasattr(self.model_service, 'get_stats'):
                stats = self.model_service.get_stats()
                stats['service_type'] = type(self.model_service).__name__
                return stats
        except Exception:
            pass

        return {
            "service_type": type(self.model_service).__name__,
            "status": "Статистика недоступна",
            "model_initialized": hasattr(self.model_service, 'is_initialized') and
                               self.model_service.is_initialized()
        }

# Глобальный экземпляр
chat_service = ChatService()