# /services/chat_service.py
import re
import time  # <-- ДОБАВИТЬ ЭТОТ ИМПОРТ
import traceback
from typing import Tuple, List, Dict, Any, Optional
from models.enums import MessageRole

class ChatService:
    """Сервис для логики чата"""
    
    def __init__(self):
        from container import container
        self.config = container.get_config()
        self.dialog_service = container.get_dialog_service()
        
        # Получаем model_service через контейнер
        self.model_service = container.get_model_service()
        
        # Определяем тип сервиса для логирования
        self.service_type = type(self.model_service).__name__
        print(f"📊 Используется {self.service_type}")
    
    def process_message(self, prompt: str, dialog_id: Optional[str] = None, 
                    max_tokens: Optional[int] = None,
                    temperature: Optional[float] = None,
                    enable_thinking: Optional[bool] = None) -> Tuple[List[Dict], str, str]:
        """Обрабатывает входящее сообщение"""
        try:
            # Валидация ввода
            if not prompt or not prompt.strip():
                return [], "⚠️ Введите сообщение", dialog_id or ""
            
            # Получаем или создаем диалог
            if not dialog_id:
                dialog_id = self.dialog_service.create_dialog()
            
            # Получаем диалог
            dialog = self.dialog_service.get_dialog(dialog_id)
            if not dialog:
                return [], "Ошибка: диалог не найден", dialog_id
            
            # Определяем параметры генерации
            if max_tokens is None:
                max_tokens = self.config.generation.default_max_tokens
            if temperature is None:
                temperature = self.config.generation.default_temperature
            if enable_thinking is None:
                enable_thinking = self.config.generation.default_enable_thinking
            
            print(f"🎯 Параметры: tokens={max_tokens}, temp={temperature}, thinking={enable_thinking}")
            
            # Форматируем историю ДО использования
            formatted_history = []
            for msg in dialog.history:
                formatted_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            
            # Добавляем новое сообщение пользователя
            formatted_history.append({"role": "user", "content": prompt.strip()})
            
            print(f"📨 Запрос: {prompt[:50]}...")
            print(f"   История: {len(formatted_history)} сообщений")
            
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
                gen_time = time.time() - start_time
                print(f"⏱️ Время генерации: {gen_time:.2f} сек")
            else:
                response_text = "Ошибка: сервис модели не поддерживается"
            
            # Добавляем сообщения в диалог
            self.dialog_service.add_message(dialog_id, MessageRole.USER, prompt)
            self.dialog_service.add_message(dialog_id, MessageRole.ASSISTANT, response_text)
            
            # Генерируем название для первого сообщения
            if len(dialog.history) == 0:
                self._generate_chat_name_simple(dialog_id, prompt)
            
            # Получаем обновленную историю
            dialog = self.dialog_service.get_dialog(dialog_id)
            display_history = dialog.to_ui_format()
            
            print(f"✅ Ответ готов ({len(response_text)} символов)")
            return display_history, "", dialog_id
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return [], f"⚠️ Ошибка: {str(e)[:100]}", dialog_id or ""
    
    def _generate_chat_name_simple(self, dialog_id: str, prompt: str):
        """Генерирует простое осмысленное название из промпта"""
        try:
            if not prompt or not isinstance(prompt, str):
                return
            
            # Очищаем промпт от мусора
            clean_prompt = re.sub(r'[^\w\s]', ' ', prompt.lower())
            words = clean_prompt.split()
            
            if not words:
                return
            
            # Убираем стоп-слова
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
            for word in words[:10]:  # Берем первые 10 слов
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
                # Fallback: берем первые 3 слова из промпта
                chat_name = ' '.join(words[:3]) if len(words) >= 3 else prompt[:30]
            
            # Капитализируем первую букву и ОЧИЩАЕМ от переносов строк
            chat_name = chat_name.strip().capitalize()
            chat_name = chat_name.replace('\n', ' ').replace('\r', ' ')
            chat_name = ' '.join(chat_name.split())  # Убираем лишние пробелы
            
            if len(chat_name) > 50:
                chat_name = chat_name[:47] + '...'
            
            # Обновляем название диалога
            self.dialog_service.rename_dialog(dialog_id, chat_name)
            print(f"✅ Название чата: {chat_name}")
            
        except Exception as e:
            print(f"⚠️ Ошибка при генерации названия: {e}")
            try:
                # Очищаем название от переносов строк
                simple_name = prompt[:40] + ('...' if len(prompt) > 40 else '')
                simple_name = simple_name.replace('\n', ' ').replace('\r', ' ')
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
        except Exception as e:
            print(f"⚠️ Ошибка при получении истории чата: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику генерации"""
        try:
            if hasattr(self.model_service, 'get_stats'):
                stats = self.model_service.get_stats()
                stats['service_type'] = self.service_type
                return stats
            else:
                return {
                    "service_type": self.service_type,
                    "status": "Статистика недоступна",
                    "model_initialized": hasattr(self.model_service, 'is_initialized') and 
                                       self.model_service.is_initialized()
                }
        except Exception as e:
            return {
                "service_type": self.service_type,
                "error": str(e),
                "status": "Ошибка получения статистики"
            }

# Глобальный экземпляр
chat_service = ChatService()