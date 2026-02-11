# services/context/manager.py
"""
Менеджер контекста диалога с многоуровневой суммаризацией
"""
import asyncio
import threading
import json
import os
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from typing import List as TypingList

from models.dialog import Dialog
from models.context import DialogContextState, InteractionChunk, L2SummaryBlock, MessageInteraction, CumulativeContext, ChunkType
from models.enums import MessageRole
from services.context.summary_manager import SummaryManager
from services.context.utils import parse_text_to_interactions, group_interactions_into_chunks, format_interaction_for_summary, extract_message_indices_from_interactions

@dataclass
class SimpleInteraction:
    """Упрощенная версия взаимодействия для внутреннего использования"""
    user_message: str
    assistant_message: str
    message_indices: TypingList[int] = None
    
    def __post_init__(self):
        if self.message_indices is None:
            self.message_indices = []
    
    @property
    def text(self) -> str:
        """Текст взаимодействия"""
        return f"Пользователь: {self.user_message}\nАссистент: {self.assistant_message}"
    
    @property
    def char_count(self) -> int:
        """Количество символов"""
        return len(self.text)

class ContextManager:
    """Управляет контекстом диалога с многоуровневой суммаризацией"""
    
    def __init__(self, dialog: Dialog, config: Dict[str, Any]):
        self.dialog = dialog
        self.config = config
        
        # Проверяем, включена ли предзагрузка
        summarizers_config = config.get("summarizers", {})
        if summarizers_config.get("preload", True):
            # Если предзагрузка включена, модели уже должны быть загружены
            from services.context.summarizers import SummarizerFactory
            if not SummarizerFactory.is_preloaded():
                print(f"⚠️ Предзагрузка включена, но модели не предзагружены для диалога {dialog.id}")
        
        # Сохраняем текущий event loop
        try:
            self._event_loop = asyncio.get_event_loop()
        except RuntimeError:
            # Если нет текущего event loop, создаем новый
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
        
        self.state = DialogContextState(
            raw_tail_char_limit=config.get("raw_tail", {}).get("char_limit", 2000),
            l1_summary_threshold=config.get("summarization", {}).get("l2_trigger_count", 4),
        )
        
        # Менеджер суммаризации
        self.summary_manager = SummaryManager(config)
        self.summary_manager.start()
        
        # Загружаем из сохраненного состояния или инициализируем
        self._state_file_path = self._get_state_file_path()
        self._load_or_initialize()
    
    def _get_state_file_path(self) -> str:
        """Генерирует путь к файлу состояния контекста с микросекундами"""
        from container import container
        config_service = container.get("config_service")
        config = config_service.get_config()
        save_dir = config.get("dialogs", {}).get("save_dir", "saved_dialogs")
        
        # Получаем имя папки из даты создания диалога с микросекундами
        datetime_str = self.dialog.created.strftime("%Y%m%dT%H%M%S")
        microseconds = self.dialog.created.strftime("%f")[:3]  # Берем только первые 3 цифры
        chat_folder = f"chat_{datetime_str}-{microseconds}"
        folder_path = os.path.join(save_dir, chat_folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # Имя файла контекста с микросекундами
        context_file = f"context_{datetime_str}-{microseconds}.chat"
        return os.path.join(folder_path, context_file)
    
    def _load_or_initialize(self):
        """Загружает сохраненное состояние или инициализирует новое"""
        if os.path.exists(self._state_file_path):
            if self.load_state(self._state_file_path):
                print(f"✅ Загружено состояние контекста из: {os.path.basename(self._state_file_path)}")
                return
        
        # Если нет сохраненного состояния, инициализируем из полной истории
        print(f"🔄 Инициализация контекста из истории для диалога {self.dialog.id}")
        self._rebuild_from_history()
        
        # Сохраняем начальное состояние
        self.save_state(self._state_file_path)
    
    def _rebuild_from_history(self):
        """Перестраивает контекст из полной истории диалога - ТОЛЬКО ДЛЯ НОВЫХ ДИАЛОГОВ"""
        # Для существующих диалогов просто инициализируем пустое состояние
        # Суммаризации будут загружены из .chat файла если он существует
        self.state = DialogContextState(
            raw_tail_char_limit=self.state.raw_tail_char_limit,
            l1_summary_threshold=self.state.l1_summary_threshold,
            cumulative_context=CumulativeContext()
        )
        
        print(f"🆕 Инициализирован новый контекст для диалога {self.dialog.id}")
    
    def _get_current_message_indices(self) -> List[int]:
        """Получает индексы текущих сообщений пользователя и ассистента"""
        indices = []
        
        # Ищем последнее сообщение пользователя
        user_found = False
        assistant_found = False
        
        for i, msg in enumerate(self.dialog.history):
            if msg.role == MessageRole.USER:
                indices.append(i)
                user_found = True
            elif msg.role == MessageRole.ASSISTANT:
                indices.append(i)
                assistant_found = True
        
        # Если не нашли оба индекса, используем последние
        if not user_found and self.dialog.history:
            indices.append(len(self.dialog.history) - 1)
        if not assistant_found and self.dialog.history:
            indices.append(len(self.dialog.history) - 1)
        
        # Сортируем и возвращаем уникальные значения
        return sorted(set(indices))
    
    def add_interaction(self, user_message: str, assistant_message: str):
        """Добавляет новое взаимодействие с правильной логикой проверки переполнения"""
        # Создаем взаимодействие
        interaction = MessageInteraction(
            user_message=user_message,
            assistant_message=assistant_message,
            user_timestamp=datetime.now(),
            assistant_timestamp=datetime.now(),
            message_indices=self._get_current_message_indices()
        )
        
        interaction_text = interaction.text + "\n\n"
        interaction_chars = len(interaction_text)
        
        print(f"📝 Добавляем взаимодействие. Текущий raw_tail: {len(self.state.raw_tail)} символов, лимит: {self.state.raw_tail_char_limit}")
        
        # ВАЖНО: Проверяем, не переполнен ли УЖЕ сырой хвост ПЕРЕД добавлением
        if len(self.state.raw_tail) > self.state.raw_tail_char_limit:
            # Сырой хвост уже переполнен (например, из-за предыдущего очень длинного взаимодействия)
            print(f"⚠️ Raw tail уже переполнен ({len(self.state.raw_tail)} > {self.state.raw_tail_char_limit}). Отправляем на суммаризацию L1")
            
            # Сохраняем переполненный хвост для суммаризации
            raw_tail_to_summarize = self.state.raw_tail
            
            # Очищаем хвост - он будет пустым перед добавлением нового взаимодействия
            self.state.raw_tail = ""
            
            # Запускаем суммаризацию переполненного хвоста
            asyncio.run_coroutine_threadsafe(
                self._trigger_l1_summarization_for_full_tail(raw_tail_to_summarize),
                self._event_loop
            )
            
            # После очистки raw_tail пустой, добавляем новое взаимодействие
            self.state.raw_tail = interaction_text
        else:
            # Сырой хвост не переполнен, просто добавляем новое взаимодействие
            # (даже если после добавления он станет больше лимита - это нормально)
            self.state.raw_tail += interaction_text
        
        # Обновляем статистику
        self.state.total_interactions += 1
        self.state.total_characters_processed += interaction_chars
        
        # Сохраняем состояние
        self.save_state(self._state_file_path)
        
        print(f"✅ Взаимодействие добавлено. Теперь raw_tail: {len(self.state.raw_tail)} символов")
        
        # Логируем состояние для отладки
        if len(self.state.raw_tail) > self.state.raw_tail_char_limit:
            print(f"📊 Raw tail теперь превышает лимит на {len(self.state.raw_tail) - self.state.raw_tail_char_limit} символов")
    
    async def _trigger_l1_summarization_for_full_tail(self, raw_tail_text: str):
        """Запускает суммаризацию L1 для всего переполненного сырого хвоста"""
        # Парсим текст хвоста на взаимодействия
        simple_interactions = parse_text_to_interactions(raw_tail_text)
        
        if not simple_interactions:
            print("⚠️ Нет взаимодействий для суммаризации в переполненном raw_tail")
            return
        
        print(f"🚀 Запуск L1 суммаризации для {len(simple_interactions)} взаимодействий")
        
        config = self.config.get("l1_chunks", {})
        target_chars = config.get("target_char_limit", 1000)
        max_chars = config.get("max_char_limit", 8000)  # Используем новый лимит
        allow_overflow = config.get("allow_single_interaction_overflow", True)  # Новая опция
        
        # Группируем ВСЕ взаимодействия с учетом разрешения переполнения
        chunks = group_interactions_into_chunks(
            simple_interactions,
            target_chars,
            allow_overflow=allow_overflow  # Передаем новую опцию
        )
        
        # Получаем параметры суммаризации
        summarization_params = self.config.get("summarization_params", {}).get("l1", {})
        
        # Суммаризируем каждый чанк
        for chunk_interactions in chunks:
            # Форматируем взаимодействия для суммаризации
            chunk_text = "\n\n".join(
                format_interaction_for_summary(interaction) 
                for interaction in chunk_interactions
            )
            
            # Логируем размер чанка
            chunk_size = len(chunk_text)
            interaction_count = len(chunk_interactions)
            print(f"  Чанк: {interaction_count} взаимодействий, {chunk_size} символов")
            
            # Извлекаем индексы сообщений
            all_message_indices = extract_message_indices_from_interactions(chunk_interactions)
            
            # Запускаем L1 суммаризацию
            self.summary_manager.schedule_l1_summary(
                chunk_text,
                callback=lambda summary, original: self._on_l1_summary_complete(
                    summary, original, all_message_indices
                ),
                **summarization_params
            )
    
    def _on_l1_summary_complete(self, summary: str, original_text: str, message_indices: List[int]):
        """Callback при завершении L1 суммаризации"""
        original_char_count = len(original_text)
        compression_ratio = original_char_count / max(len(summary), 1)
        target_compression = self.config.get("l1_chunks", {}).get("compression_ratio", 12.0)
        
        print(f"✅ L1 суммаризация завершена: {original_char_count} -> {len(summary)} символов (сжатие: {compression_ratio:.1f}x)")
        
        # Создаем чанк L1 (только с суммаризацией)
        chunk = InteractionChunk.create_from_summary(
            summary=summary,
            original_char_count=original_char_count,
            message_indices=message_indices
        )
        chunk.chunk_type = ChunkType.L1_SUMMARY
        
        self.state.l1_chunks.append(chunk)
        self.state.total_summarizations_l1 += 1
        self.state.last_summarization_time = datetime.now()
        
        # Сохраняем состояние (только суммаризации)
        self.save_state(self._state_file_path)
        
        # Проверяем, не пора ли запустить L2 суммаризацию
        if len(self.state.l1_chunks) >= self.state.l1_summary_threshold:
            asyncio.run_coroutine_threadsafe(
                self._trigger_l2_summarization(),
                self._event_loop
            )
    
    async def _trigger_l2_summarization(self):
        """Запускает суммаризацию L2"""
        # Берем половина старейших чанков
        half = max(1, len(self.state.l1_chunks) // 2)
        chunks_to_summarize = self.state.l1_chunks[:half]
        
        if not chunks_to_summarize:
            return
        
        print(f"🚀 Запуск L2 суммаризации для {len(chunks_to_summarize)} чанков")
        
        # Получаем параметры L2 суммаризации из конфига
        summarization_params = self.config.get("summarization_params", {}).get("l2", {})
        
        # Подготавливаем текст для суммаризации (объединяем суммаризации L1)
        l1_summaries_text = "\n---\n".join(chunk.summary for chunk in chunks_to_summarize)
        total_original_chars = sum(chunk.original_char_count for chunk in chunks_to_summarize)
        l1_chunk_ids = [chunk.id for chunk in chunks_to_summarize]
        
        # Запускаем фоновую задачу
        self.summary_manager.schedule_l2_summary(
            l1_summaries_text,
            original_char_count=total_original_chars,
            l1_chunk_ids=l1_chunk_ids,
            callback=lambda summary, original_text, chunk_ids, total_chars: self._on_l2_summary_complete(
                summary, chunk_ids, total_chars
            ),
            **summarization_params
        )
    
    def _on_l2_summary_complete(self, summary: str, l1_chunk_ids: List[str], total_original_chars: int):
        """Callback при завершении L2 суммаризации"""
        compression_ratio = total_original_chars / max(len(summary), 1)
        target_compression = self.config.get("l2_summary", {}).get("compression_ratio", 30.0)
        
        print(f"✅ L2 суммаризация завершена: {len(l1_chunk_ids)} чанков, {total_original_chars} -> {len(summary)} символов (сжатие: {compression_ratio:.1f}x)")
        
        # Создаем блок L2 (только с суммаризацией)
        l2_block = L2SummaryBlock.create_from_summary(
            chunk_ids=l1_chunk_ids,
            summary=summary,
            original_char_count=total_original_chars
        )
        l2_block.chunk_type = ChunkType.L2_SUMMARY
        
        # Добавляем в кумулятивную строку
        self.state.cumulative_context.add_block(l2_block)
        
        # Удаляем обработанные чанки L1
        self.state.l1_chunks = [
            chunk for chunk in self.state.l1_chunks 
            if chunk.id not in l1_chunk_ids
        ]
        
        # Добавляем блок L2
        self.state.l2_blocks.append(l2_block)
        
        self.state.total_summarizations_l2 += 1
        self.state.last_summarization_time = datetime.now()
        
        # Сохраняем состояние
        self.save_state(self._state_file_path)
    
    def get_context_for_generation(self) -> str:
        """Возвращает контекст для генерации с четким разделением уровней"""
        context_parts = []
        
        # Системное сообщение с инструкцией
        system_message = """Ты получаешь контекст диалога в нескольких частях:

1. <sum_block>...</sum_block> - кумулятивные суммаризации всего диалога (высший уровень обобщения)
2. ## Чанк: - конспекты групп сообщений среднего уровня детализации
3. Последние сообщения - полный текст последней части диалога (максимальная детализация)

Внимательно изучи ВЕСЬ предоставленный контекст перед ответом. Особое внимание уделяй последним сообщениям."""
        
        context_parts.append(system_message)
        
        # 1. Кумулятивная строка P (суммаризации L2)
        if self.state.cumulative_context.content:
            formatted_cumulative = self.state.cumulative_context.get_formatted()
            context_parts.append(formatted_cumulative)
        
        # 2. Чанки L1 (если есть)
        if self.state.l1_chunks:
            l1_context = "# Конспекты недавних обсуждений (средний уровень детализации):\n"
            
            # Группируем чанки по тематике для лучшего восприятия
            for i, chunk in enumerate(self.state.l1_chunks, 1):
                l1_context += f"\n## Чанк {i}:\n{chunk.summary}\n"
            
            context_parts.append(l1_context)
        
        # 3. Сырой хвост (последние n символов)
        if self.state.raw_tail:
            raw_context = "# Последние сообщения (полный текст, максимальная детализация):\n"
            raw_context += self.state.raw_tail
            context_parts.append(raw_context)
        
        # Добавляем разделитель между контекстом и текущим диалогом
        context_parts.append("\n" + "="*50 + "\n")
        
        return "\n\n".join(context_parts)
    
    def save_state(self, file_path: str = None) -> bool:
        """Сохраняет состояние контекста в файл (только суммаризации)"""
        if file_path is None:
            file_path = self._state_file_path
            
        try:
            # Создаем полный словарь состояния (только суммаризации)
            state_dict = self.state.model_dump_jsonable()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения состояния контекста: {e}")
            return False
    
    def load_state(self, file_path: str) -> bool:
        """Загружает состояние контекста из файла (только суммаризации)"""
        try:
            if not os.path.exists(file_path):
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            
            # Восстанавливаем состояние из словаря
            self.state = DialogContextState.model_validate(state_dict)
            
            print(f"✅ Загружено {len(self.state.l1_chunks)} чанков L1, "
                f"{len(self.state.l2_blocks)} блоков L2")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки состояния контекста: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику контекста"""
        return self.state.get_stats()
    
    def cleanup(self):
        """Очищает ресурсы менеджера контекста"""
        if hasattr(self, 'summary_manager'):
            self.summary_manager.stop()
        self.save_state()