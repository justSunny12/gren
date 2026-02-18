# services/search/manager.py
"""
SearchManager — оркестратор поискового флоу.

Знает про Pass 1 (решение), клиент Tavily и форматирование,
но не знает про стриминг и UI — это задача stream_processor.
"""
from dataclasses import dataclass
from typing import List, Optional

from .client import TavilyClient, SearchResult
from .decision import SearchDecisionService, DecisionResult
from .formatter import format_results_for_model, build_augmented_messages


@dataclass
class SearchOutcome:
    """Результат работы SearchManager."""
    searched: bool                        # Был ли выполнен поиск
    query: str                            # Поисковый запрос (если searched)
    results: List[SearchResult]           # Сырые результаты
    augmented_messages: List[dict]        # Сообщения с инжектированным контекстом
    error: Optional[str] = None          # Ошибка (если была)


class SearchManager:
    """
    Публичный интерфейс поискового сервиса.
    Создаётся один раз через контейнер.
    """

    def __init__(self, config: dict):
        self.config = config
        search_cfg = config.get("search", {})
        tavily_cfg = search_cfg.get("tavily", {})
        results_cfg = search_cfg.get("results", {})

        self.decision_service = SearchDecisionService(search_cfg)
        self.client = TavilyClient(
            api_key=search_cfg.get("api_key", ""),
            timeout=tavily_cfg.get("timeout", 10),
        )
        self.max_results = tavily_cfg.get("max_results", 3)
        self.search_depth = tavily_cfg.get("search_depth", "basic")
        self.max_content_chars = results_cfg.get("max_content_chars", 1500)
        self.max_total_chars = results_cfg.get("max_total_chars", 5000)

        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            from container import container
            self._logger = container.get_logger()
        return self._logger

    async def process(
        self,
        user_prompt: str,
        original_messages: List[dict],
    ) -> SearchOutcome:
        """
        Полный цикл: Pass1 → поиск → форматирование.

        Возвращает SearchOutcome. При любой ошибке возвращает
        searched=False и исходные messages — генерация продолжается
        без поиска (fail-safe).
        """
        self.logger.info(f"📡 SearchManager.process started for prompt: {user_prompt[:50]}...")

        # Pass 1: нужен ли поиск?
        decision: DecisionResult = await self.decision_service.should_search(user_prompt)
        self.logger.info(f"📡 Decision: needs_search={decision.needs_search}, query='{decision.query}'")
        self.logger.info(f"📡 Raw decision response: {decision.raw_response}")

        if not decision.needs_search:
            return SearchOutcome(
                searched=False,
                query="",
                results=[],
                augmented_messages=original_messages,
            )

        self.logger.info("🔍 Выполняю Tavily запрос...")
        try:
            results = await self.client.search(
                query=decision.query,
                max_results=self.max_results,
                search_depth=self.search_depth,
            )
            self.logger.info(f"🔍 Tavily вернул {len(results)} результатов")
        except Exception as e:
            self.logger.error(f"❌ Tavily API error: {e}")
            return SearchOutcome(
                searched=False,
                query=decision.query,
                results=[],
                augmented_messages=original_messages,
                error=str(e),
            )

        if not results:
            self.logger.warning(f"Tavily вернул 0 результатов для: {decision.query}")
            return SearchOutcome(
                searched=False,
                query=decision.query,
                results=[],
                augmented_messages=original_messages,
            )

        self.logger.info("  ✅ Получено результатов: %d", len(results))

        # Форматирование и инжекция в messages
        search_context = format_results_for_model(
            results=results,
            query=decision.query,
            max_content_chars=self.max_content_chars,
            max_total_chars=self.max_total_chars,
        )
        augmented = build_augmented_messages(original_messages, search_context)

        return SearchOutcome(
            searched=True,
            query=decision.query,
            results=results,
            augmented_messages=augmented,
        )