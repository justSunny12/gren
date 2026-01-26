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
            
            # Определяем параметры генерации
            if max_tokens is None:
                max_tokens = self.config.generation.default_max_tokens
            if temperature is None:
                temperature = self.config.generation.default_temperature
            if enable_thinking is None:
                enable_thinking = self.config.generation.default_enable_thinking
            
            # Форматируем историю
            formatted_history = []
            for msg in dialog_before.history:
                formatted_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            
            formatted_history.append({"role": "user", "content": prompt.strip()})
            
            # Генерируем ответ
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
            return [], f"⚠️ Ошибка: {str(e)[:100]}", dialog_id or ""
    
    def _generate_chat_name_simple(self, dialog_id: str, prompt: str):
        """Генерирует простое осмысленное название из промпта"""
        try:
            if not prompt or not isinstance(prompt, str):
                return
            
            clean_prompt = re.sub(r'[^\w\s]', ' ', prompt.lower())
            words = clean_prompt.split()
            
            if not words:
                return
            
            stop_words = {
                'привет', 'здравствуй', 'здравствуйте', 'здрасьте', 'хай', 'хелло', 
                'hello', 'hi', 'как', 'дела', 'что', 'ты', 'вы', 'мне', 'меня', 
                'мной', 'твой', 'ваш', 'это', 'тот', 'этот', 'такой', 'который', 
                'свой', 'можно', 'мог', 'могу', 'можешь', 'можете', 'помоги', 
                'помощь', 'пожалуйста', 'пжлст', 'плз', 'plz', 'спасибо', 'thanks', 
                'thank', 'ну', 'вот', 'так', 'же', 'бы', 'ли', 'то', 'либо', 'нибудь',
                'а', 'и', 'но', 'или', 'да', 'нет', 'не', 'ни', 'уже', 'еще', 'уж',
                'ещё', 'очень', 'хочу', 'хотел', 'хотела', 'хотелось', 'хотеть',
                'сделай', 'напиши', 'объясни', 'расскажи', 'покажи', 'вопрос',
                'ответ', 'информация', 'инфа', 'инфо', 'просто', 'самый', 'сама',
                'само', 'свои', 'свой', 'своих', 'чтобы', 'зачем', 'почему',
                'когда', 'где', 'кто', 'чем', 'какой', 'какая', 'какое', 'какие'
            }
            
            meaningful_words = []
            for word in words[:10]:
                if (len(word) > 2 and 
                    word not in stop_words and 
                    word not in meaningful_words):
                    meaningful_words.append(word)
            
            # Формируем название
            if meaningful_words:
                if len(meaningful_words) > 4:
                    chat_name = ' '.join(meaningful_words[:4])
                else:
                    chat_name = ' '.join(meaningful_words)
            else:
                chat_name = ' '.join(words[:3]) if len(words) >= 3 else prompt[:30]
            
            # Капитализируем первую букву и очищаем
            chat_name = chat_name.strip().capitalize()
            chat_name = chat_name.replace('\n', ' ').replace('\r', ' ')
            chat_name = ' '.join(chat_name.split())
            
            if len(chat_name) > 50:
                chat_name = chat_name[:47] + '...'
            
            # Обновляем название диалога
            self.dialog_service.rename_dialog(dialog_id, chat_name)
            
        except Exception:
            try:
                simple_name = prompt[:40] + ('...' if len(prompt) > 40 else '')
                simple_name = simple_name.replace('\n', ' ').replace('\r', ' ')
                simple_name = simple_name.strip()
                self.dialog_service.rename_dialog(dialog_id, simple_name)
            except:
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