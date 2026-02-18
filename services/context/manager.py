# services/context/manager.py
"""
Менеджер контекста диалога с многоуровневой суммаризацией.
После рефакторинга использует выделенные компоненты.
"""
import asyncio
import threading
from datetime import datetime
from typing import List, Dict, Any

from models.dialog import Dialog
from models.context import DialogContextState, InteractionChunk, ChunkType
from models.enums import MessageRole
from services.context.summary_manager import SummaryManager
from services.context.trigger import SummarizationTrigger
from services.context.persistence import ContextStatePersistence
from services.context.builder import ContextBuilder
from services.context.utils import parse_text_to_interactions, group_interactions_into_chunks, format_interaction_for_summary, extract_message_indices_from_interactions
from .interaction import SimpleInteraction


class ContextManager:
    """Управляет контекстом диалога с многоуровневой суммаризацией."""

    def __init__(self, dialog: Dialog, config: Dict[str, Any]):
        self.dialog = dialog
        self.config = config

        # Сохраняем event loop
        try:
            self._event_loop = asyncio.get_event_loop()
        except RuntimeError:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

        # Инициализация компонентов
        self.trigger = SummarizationTrigger(config)
        self.persistence = ContextStatePersistence(dialog, config)
        self.builder = ContextBuilder()
        self.summary_manager = SummaryManager(config)
        self.summary_manager.start()

        # Загрузка или создание состояния
        self.state = self._load_or_initialize()

        # Блокировка для защиты состояния
        self._state_lock = threading.RLock()

    def _load_or_initialize(self) -> DialogContextState:
        """Загружает сохранённое состояние или создаёт новое."""
        loaded = self.persistence.load()
        if loaded:
            return loaded

        # Создание нового состояния с параметрами из конфига
        structure = self.config.get("structure", {})
        raw_tail_config = structure.get("raw_tail", {})
        thresholds = structure.get("thresholds", {})

        return DialogContextState(
            raw_tail_char_limit=raw_tail_config.get("char_limit", 2000),
            l1_summary_threshold=thresholds.get("l2_trigger_count", 4),
            l2_preserve_ratio=thresholds.get("l2_preserve_ratio", 0.5)
        )

    def add_interaction(self, user_message: str, assistant_message: str):
        """Добавляет новое взаимодействие (вызывается из основного потока)."""
        with self._state_lock:
            interaction = SimpleInteraction(
                user_message=user_message,
                assistant_message=assistant_message,
                message_indices=self._get_current_message_indices()
            )
            interaction_text = interaction.text + "\n\n"
            interaction_chars = len(interaction_text)

            # Проверка переполнения raw_tail
            if self.trigger.should_trigger_l1(self.state.raw_tail):
                # Уже переполнен → суммаризируем всё и очищаем
                raw_tail_to_summarize = self.state.raw_tail
                self.state.raw_tail = ""
                asyncio.run_coroutine_threadsafe(
                    self._trigger_l1_summarization_for_full_tail(raw_tail_to_summarize),
                    self._event_loop
                )
                self.state.raw_tail = interaction_text
            else:
                self.state.raw_tail += interaction_text

            # Статистика
            self.state.total_interactions += 1
            self.state.total_characters_processed += interaction_chars

            # Сохранение
            self.persistence.save(self.state)

    def _get_current_message_indices(self) -> List[int]:
        """Возвращает индексы последних сообщений пользователя и ассистента."""
        indices = []
        for i, msg in enumerate(self.dialog.history):
            if msg.role in (MessageRole.USER, MessageRole.ASSISTANT):
                indices.append(i)
        return sorted(set(indices)) or [len(self.dialog.history)-1]

    async def _trigger_l1_summarization_for_full_tail(self, raw_tail_text: str):
        """Запускает L1 суммаризацию для всего raw_tail (выполняется в основном event loop)."""
        interactions = parse_text_to_interactions(raw_tail_text)
        if not interactions:
            return

        l1_config = self.config.get("structure", {}).get("l1_chunks", {})
        target_chars = l1_config.get("target_char_limit", 1000)
        allow_overflow = l1_config.get("allow_single_interaction_overflow", True)

        chunks = group_interactions_into_chunks(interactions, target_chars, allow_overflow)

        summarization_params = self.config.get("models", {}).get("generation_params", {}).get("l1", {})

        for chunk_interactions in chunks:
            chunk_text = "\n\n".join(format_interaction_for_summary(i) for i in chunk_interactions)
            message_indices = extract_message_indices_from_interactions(chunk_interactions)

            self.summary_manager.schedule_l1_summary(
                chunk_text,
                callback=lambda summary, original: self._on_l1_summary_complete(
                    summary, original, message_indices
                ),
                **summarization_params
            )

    def _on_l1_summary_complete(self, summary: str, original_text: str, message_indices: List[int]):
        """Обработка завершения L1 суммаризации (вызывается из фонового потока воркера)."""
        with self._state_lock:
            chunk = InteractionChunk.create_from_summary(
                summary=summary,
                original_char_count=len(original_text),
                message_indices=message_indices
            )
            chunk.chunk_type = ChunkType.L1_SUMMARY

            self.state.l1_chunks.append(chunk)
            self.state.total_summarizations_l1 += 1
            self.state.last_summarization_time = self.state.last_summarization_time or datetime.now()

            self.persistence.save(self.state)

            # Проверка на L2
            if self.trigger.should_trigger_l2(len(self.state.l1_chunks)):
                asyncio.run_coroutine_threadsafe(
                    self._trigger_l2_summarization(),
                    self._event_loop
                )

    async def _trigger_l2_summarization(self):
        """Запускает L2 суммаризацию (выполняется в основном event loop)."""
        with self._state_lock:
            if not self.state.l1_chunks:
                return

            ratio = self.state.l2_preserve_ratio
            ratio = max(0.1, min(1.0, ratio))
            chunk_count = max(1, int(len(self.state.l1_chunks) * ratio))
            chunks_to_summarize = self.state.l1_chunks[:chunk_count]

            l1_summaries_text = "\n---\n".join(c.summary for c in chunks_to_summarize)
            total_original_chars = sum(c.original_char_count for c in chunks_to_summarize)
            l1_chunk_ids = [c.id for c in chunks_to_summarize]

            summarization_params = self.config.get("summarization_params", {}).get("l2", {})

            self.summary_manager.schedule_l2_summary(
                l1_summaries_text,
                original_char_count=total_original_chars,
                l1_chunk_ids=l1_chunk_ids,
                callback=self._on_l2_summary_complete,
                **summarization_params
            )

    def _on_l2_summary_complete(self, summary: str, original_text: str, l1_chunk_ids: List[str], original_char_count: int):
        """Обработка завершения L2 суммаризации (вызывается из фонового потока воркера)."""
        with self._state_lock:
            from models.context import L2SummaryBlock
            l2_block = L2SummaryBlock.create_from_summary(
                chunk_ids=l1_chunk_ids,
                summary=summary,
                original_char_count=original_char_count
            )
            l2_block.chunk_type = ChunkType.L2_SUMMARY

            self.state.cumulative_context.add_block(l2_block)
            self.state.l1_chunks = [c for c in self.state.l1_chunks if c.id not in l1_chunk_ids]
            self.state.l2_blocks.append(l2_block)
            self.state.total_summarizations_l2 += 1
            self.state.last_summarization_time = self.state.last_summarization_time or datetime.now()

            self.persistence.save(self.state)

    def get_context_for_generation(self) -> str:
        """Возвращает контекст для передачи модели (только чтение, но для согласованности используем блокировку)."""
        with self._state_lock:
            return self.builder.build(self.state, len(self.dialog.history))

    def save_state(self, file_path: str = None) -> bool:
        """Сохраняет текущее состояние."""
        with self._state_lock:
            return self.persistence.save(self.state, file_path)

    def load_state(self, file_path: str) -> bool:
        """Загружает состояние из файла."""
        with self._state_lock:
            loaded = self.persistence.load(file_path)
            if loaded:
                self.state = loaded
                return True
            return False

    def cleanup(self):
        """Освобождает ресурсы."""
        self.summary_manager.stop()