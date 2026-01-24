# /services/chat_service.py
import re
import torch
from typing import Tuple, List, Dict, Any, Optional
from models.enums import MessageRole

class ChatService:
    """Сервис для логики чата"""
    
    def __init__(self):
        # Ленивый импорт container
        from container import container
        self.config = container.get_config()
        self.model_service = container.get_model_service()
        self.dialog_service = container.get_dialog_service()
    
    def initialize_model(self):
        """Инициализирует модель (ленивая загрузка)"""
        return self.model_service.initialize()
    
    def process_message(self, prompt: str, dialog_id: Optional[str] = None, 
                       max_tokens: Optional[int] = None,
                       temperature: Optional[float] = None) -> Tuple[List[Dict], str, str]:
        """Обрабатывает входящее сообщение и генерирует ответ"""
        if not prompt.strip():
            return [], "⚠️ Введите сообщение", dialog_id or ""
        
        # Получаем или создаем диалог
        if not dialog_id:
            dialog_id = self.dialog_service.create_dialog()
        
        # Получаем модель и токенизатор
        model, tokenizer, generate_lock = self.initialize_model()
        
        # Получаем историю диалога
        dialog = self.dialog_service.get_dialog(dialog_id)
        if not dialog:
            return [], "Ошибка: диалог не найден", dialog_id
        
        # Проверяем, первое ли это сообщение
        is_first_message = len(dialog.history) == 0
        
        # Форматируем историю для модели
        formatted_history = []
        for msg in dialog.history:
            formatted_history.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        formatted_history.append({"role": "user", "content": prompt})
        
        # Подготавливаем текст для модели
        text = tokenizer.apply_chat_template(
            formatted_history,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Получаем параметры генерации
        gen_params = self.model_service.get_generation_params(
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Генерируем ответ
        response_text = ""
        with generate_lock:
            inputs = tokenizer(text, return_tensors="pt").to(model.device)
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    **gen_params
                )
            
            input_length = inputs.input_ids.shape[1]
            response_text = tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)
        
        # Очищаем ответ
        response_text = self._clean_response(response_text)
        
        # Добавляем сообщения в диалог
        self.dialog_service.add_message(dialog_id, MessageRole.USER, prompt)
        self.dialog_service.add_message(dialog_id, MessageRole.ASSISTANT, response_text)
        
        # Если это первое сообщение, генерируем простое название
        if is_first_message:
            self._generate_chat_name_simple(dialog_id, prompt)
        
        # Получаем обновленную историю для отображения
        dialog = self.dialog_service.get_dialog(dialog_id)
        display_history = dialog.to_ui_format()
        
        return display_history, "", dialog_id
    
    def _clean_response(self, response: str) -> str:
        """Очищает ответ от служебных тегов"""
        # Убираем тег <think> и его содержимое
        think_pattern = r'<think>.*?</think>'
        response = re.sub(think_pattern, '', response, flags=re.DOTALL)
        
        # Убираем оставшиеся теги
        response = re.sub(r'<[^>]+>', '', response)
        
        # Очищаем лишние пробелы и переносы строк
        response = re.sub(r'\n\s*\n', '\n', response)
        return response.strip()
    
    def _generate_chat_name_simple(self, dialog_id: str, prompt: str):
        """Генерирует простое осмысленное название из промпта (1-4 слова)"""
        try:
            # Очищаем промпт от мусора
            clean_prompt = re.sub(r'[^\w\s]', ' ', prompt.lower())
            words = clean_prompt.split()
            
            # Убираем стоп-слова (слишком короткие и неинформативные)
            stop_words = {'привет', 'здравствуй', 'здравствуйте', 'здрасьте', 'хай', 'хелло', 'hello', 'hi',
                         'как', 'дела', 'что', 'ты', 'вы', 'мне', 'меня', 'мной', 'твой', 'ваш',
                         'это', 'тот', 'этот', 'такой', 'который', 'свой',
                         'можно', 'мог', 'могу', 'можешь', 'можете', 'помоги', 'помощь',
                         'пожалуйста', 'пжлст', 'плз', 'plz', 'спасибо', 'thanks', 'thank',
                         'ну', 'вот', 'так', 'же', 'бы', 'ли', 'то', 'либо', 'нибудь',
                         'а', 'и', 'но', 'или', 'да', 'нет', 'не', 'ни', 'же',
                         'уже', 'еще', 'уж', 'ещё', 'очень', 'оч', 'очень',
                         'хочу', 'хотел', 'хотела', 'хотелось', 'хотеть',
                         'сделай', 'напиши', 'объясни', 'расскажи', 'покажи',
                         'вопрос', 'ответ', 'информация', 'инфа', 'инфо'}
            
            meaningful_words = []
            for word in words[:10]:  # Берем первые 10 слов
                if (len(word) > 2 and  # Слово длиннее 2 букв
                    word not in stop_words and  # Не стоп-слово
                    word not in meaningful_words):  # Не дублируется
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
            
            # Капитализируем первую букву
            chat_name = chat_name.strip().capitalize()
            
            # Обрезаем если слишком длинное
            if len(chat_name) > 50:
                chat_name = chat_name[:47] + '...'
            
            # Обновляем название диалога
            self.dialog_service.rename_dialog(dialog_id, chat_name)
            print(f"✅ Название чата: {chat_name}")
            
        except Exception as e:
            print(f"⚠️ Ошибка при генерации названия: {e}")
            # Простой fallback
            simple_name = prompt[:40] + ('...' if len(prompt) > 40 else '')
            self.dialog_service.rename_dialog(dialog_id, simple_name)
    
    def get_chat_history(self, dialog_id: Optional[str] = None) -> List[Dict]:
        """Получает историю чата"""
        if not dialog_id:
            dialog = self.dialog_service.get_current_dialog()
        else:
            dialog = self.dialog_service.get_dialog(dialog_id)
        
        if dialog:
            return dialog.to_ui_format()
        return []

# Глобальный экземпляр
chat_service = ChatService()