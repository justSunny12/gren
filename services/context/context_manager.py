# services/context/context_manager.py
"""
Менеджер контекста диалога с многоуровневой суммаризацией.
"""
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

from models.dialog import Dialog
from models.context import DialogContextState, InteractionChunk, ChunkType
from models.enums import MessageRole
from services.context.trigger import SummarizationTrigger
from services.context.persistence import ContextStatePersistence
from services.context.builder import ContextBuilder
from services.context.utils import (
    parse_text_to_interactions,
    group_interactions_into_chunks,
    format_interaction_for_summary,
    extract_message_indices_from_interactions,
)
from .interaction import SimpleInteraction
from services.context.global_manager import global_summary_manager
from container import container


class ContextManager:
    """Управляет контекстом диалога с многоуровневой суммаризацией."""

    def __init__(self, dialog: Dialog, config: Dict[str, Any]):
        self.dialog = dialog
        self.config = config
        self._logger = container.get_logger()

        self.trigger = SummarizationTrigger(config)
        self.persistence = ContextStatePersistence(dialog, config)
        self.builder = ContextBuilder()

        self.state = self._load_or_initialize()

        self._state_lock = threading.RLock()
        self._l1_in_progress = False

        # Счётчик ожидающих L1-чанков и длина обрабатываемого хвоста.
        # Инициализируются здесь, сбрасываются после завершения всех чанков.
        self._pending_l1_chunks: int = 0
        self._original_len_l1: int = 0

        self._cached_context: Optional[str] = None
        self._cached_state_hash: Optional[str] = None

    def _load_or_initialize(self) -> DialogContextState:
        loaded = self.persistence.load()
        if loaded:
            return loaded

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

            self._logger.debug(
                f"📏 [ContextManager] raw_tail до добавления: {len(self.state.raw_tail)} символов, "
                f"лимит {self.state.raw_tail_char_limit}"
            )

            if not self._l1_in_progress and self.trigger.should_trigger_l1(self.state.raw_tail):
                self._logger.debug("🚨 [ContextManager] Превышен лимит raw_tail, запускаем L1 суммаризацию")
                self._l1_in_progress = True
                raw_tail_to_summarize = self.state.raw_tail
                original_len = len(raw_tail_to_summarize)
                self._trigger_l1_summarization_for_full_tail(raw_tail_to_summarize, original_len)
                self.state.raw_tail += interaction_text
                self._logger.debug(
                    f"📏 [ContextManager] raw_tail после добавления (L1 запущена): {len(self.state.raw_tail)} символов"
                )
            else:
                self.state.raw_tail += interaction_text
                self._logger.debug(
                    f"📏 [ContextManager] raw_tail после добавления: {len(self.state.raw_tail)} символов"
                )

            self.state.total_interactions += 1
            self.state.total_characters_processed += interaction_chars
            self.state.invalidate_hash()
            self.persistence.save(self.state)

    def _get_current_message_indices(self) -> List[int]:
        indices = [
            i for i, msg in enumerate(self.dialog.history)
            if msg.role in (MessageRole.USER, MessageRole.ASSISTANT)
        ]
        return sorted(set(indices)) or [len(self.dialog.history) - 1]

    def _trigger_l1_summarization_for_full_tail(self, raw_tail_text: str, original_len: int):
        """Синхронно парсит raw_tail, разбивает на чанки и планирует L1 задачи."""
        self._logger.debug(
            f"🔍 [ContextManager] _trigger_l1_summarization_for_full_tail: "
            f"получен текст длиной {len(raw_tail_text)} символов (original_len={original_len})"
        )

        interactions = parse_text_to_interactions(raw_tail_text)
        self._logger.debug(
            f"🔍 [ContextManager] parse_text_to_interactions вернул {len(interactions)} взаимодействий"
        )

        if not interactions:
            self._logger.warning("⚠️ [ContextManager] Нет взаимодействий для суммаризации, сбрасываем флаг")
            with self._state_lock:
                self._l1_in_progress = False
            return

        l1_config = self.config.get("structure", {}).get("l1_chunks", {})
        target_chars = l1_config.get("target_char_limit", 1000)
        allow_overflow = l1_config.get("allow_single_interaction_overflow", True)

        chunks = group_interactions_into_chunks(interactions, target_chars, allow_overflow)
        self._logger.debug(
            f"🔍 [ContextManager] Сформировано {len(chunks)} чанков для L1 суммаризации"
        )

        summarization_params = self.config.get("generation_params", {}).get("l1", {})
        self._logger.debug(f"🔍 [ContextManager] Параметры L1 суммаризации: {summarization_params}")

        self._pending_l1_chunks = len(chunks)
        self._original_len_l1 = original_len

        for idx, chunk_interactions in enumerate(chunks):
            chunk_text = "\n\n".join(format_interaction_for_summary(i) for i in chunk_interactions)
            message_indices = extract_message_indices_from_interactions(chunk_interactions)
            self._logger.debug(
                f"🔍 [ContextManager] Чанк {idx+1}: длина {len(chunk_text)} символов, "
                f"сообщения {message_indices}"
            )

            global_summary_manager.schedule_l1_summary(
                dialog_id=self.dialog.id,
                text=chunk_text,
                callback=lambda summary, data: self._on_l1_summary_complete(
                    summary, data["text"], message_indices
                ),
                **summarization_params
            )

    def _on_l1_summary_complete(self, summary: str, original_text: str, message_indices: List[int]):
        """Обработка завершения L1 суммаризации (вызывается из фонового потока воркера)."""
        self._logger.debug(
            f"✅ [ContextManager] L1 суммаризация завершена, длина суммаризации {len(summary)} символов, "
            f"исходный текст {len(original_text)} символов"
        )
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
            self._logger.debug(
                f"📊 [ContextManager] L1 чанк добавлен, всего чанков: {len(self.state.l1_chunks)}"
            )

            self._pending_l1_chunks -= 1

            if self._pending_l1_chunks == 0:
                original_len = self._original_len_l1
                if len(self.state.raw_tail) >= original_len:
                    self.state.raw_tail = self.state.raw_tail[original_len:]
                    self._logger.debug(
                        f"🗑️ [ContextManager] Удалено {original_len} символов из raw_tail, "
                        f"осталось {len(self.state.raw_tail)}"
                    )
                else:
                    self._logger.warning(
                        f"⚠️ [ContextManager] raw_tail короче ожидаемого "
                        f"({len(self.state.raw_tail)} < {original_len}), возможно, данные потеряны"
                    )
                self._l1_in_progress = False
                self._original_len_l1 = 0

            self.state.invalidate_hash()
            self.persistence.save(self.state)

            if self.trigger.should_trigger_l2(len(self.state.l1_chunks)):
                self._logger.debug(
                    f"🚨 [ContextManager] Достигнут порог L2 ({len(self.state.l1_chunks)} чанков), "
                    f"запускаем L2 суммаризацию"
                )
                future = global_summary_manager.run_coro(self._trigger_l2_summarization())

                def _log_l2_future_error(fut):
                    exc = fut.exception()
                    if exc:
                        self._logger.error(
                            f"❌ [ContextManager] Ошибка в _trigger_l2_summarization: {exc}",
                            exc_info=True
                        )
                future.add_done_callback(_log_l2_future_error)

    async def _trigger_l2_summarization(self):
        """Запускает L2 суммаризацию (выполняется в фоновом event loop воркера)."""
        self._logger.debug("🔍 [ContextManager] _trigger_l2_summarization запущен")
        with self._state_lock:
            if not self.state.l1_chunks:
                self._logger.debug("🔍 [ContextManager] Нет L1 чанков для L2 суммаризации")
                return

            ratio = max(0.1, min(1.0, self.state.l2_preserve_ratio))
            chunk_count = max(1, int(len(self.state.l1_chunks) * ratio))
            chunks_to_summarize = self.state.l1_chunks[:chunk_count]
            self._logger.debug(
                f"🔍 [ContextManager] Для L2 отобрано {len(chunks_to_summarize)} чанков "
                f"(из {len(self.state.l1_chunks)}), ratio={ratio:.2f}"
            )

            l1_summaries_text = "\n---\n".join(c.summary for c in chunks_to_summarize)
            total_original_chars = sum(c.original_char_count for c in chunks_to_summarize)
            l1_chunk_ids = [c.id for c in chunks_to_summarize]

            summarization_params = self.config.get("generation_params", {}).get("l2", {})

            global_summary_manager.schedule_l2_summary(
                dialog_id=self.dialog.id,
                text=l1_summaries_text,
                original_char_count=total_original_chars,
                l1_chunk_ids=l1_chunk_ids,
                callback=lambda summary, original, chunk_ids, orig_count: self._on_l2_summary_complete(
                    summary, original, chunk_ids, orig_count
                ),
                **summarization_params
            )

    def _on_l2_summary_complete(self, summary: str, original_text: str,
                                l1_chunk_ids: List[str], original_char_count: int):
        self._logger.debug(
            f"✅ [ContextManager] L2 суммаризация завершена, длина суммаризации {len(summary)} символов"
        )
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
            self._logger.debug(
                f"📊 [ContextManager] L2 блок добавлен, удалено L1 чанков: {len(l1_chunk_ids)}, "
                f"осталось L1 чанков: {len(self.state.l1_chunks)}"
            )

            self.state.invalidate_hash()
            self.persistence.save(self.state)

    def get_context_for_generation(self) -> str:
        with self._state_lock:
            current_hash = self.state.get_hash()
            if current_hash == self._cached_state_hash and self._cached_context is not None:
                return self._cached_context
            context = self.builder.build(self.state, len(self.dialog.history))
            self._cached_context = context
            self._cached_state_hash = current_hash
            return context

    def save_state(self, file_path: str = None) -> bool:
        with self._state_lock:
            return self.persistence.save(self.state, file_path)

    def load_state(self, file_path: str) -> bool:
        with self._state_lock:
            loaded = self.persistence.load(file_path)
            if loaded:
                self.state = loaded
                self._cached_context = None
                self._cached_state_hash = None
                return True
            return False

    def cleanup(self):
        pass
