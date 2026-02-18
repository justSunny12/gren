# services/search/decision.py
"""
Pass 1: модель решает, нужен ли веб-поиск для ответа на вопрос.

Используем уже загруженную модель суммаризатора (Qwen3-4B) —
она быстрая, не блокирует основную модель и поддерживает
структурированный вывод.
"""
import json
import re
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

def _get_current_datetime_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

DECISION_SYSTEM_PROMPT = """Ты — классификатор запросов. Определяешь, нужен ли поиск в интернете.

Поиск НУЖЕН если:
- Вопрос требует актуальных данных (цены, курсы, новости, события, версии ПО)
- Нужна информация после 2024 года
- Конкретные факты о реальных людях, компаниях, продуктах (не общеизвестные)
- Прогнозы погоды, расписания, статусы

Поиск НЕ НУЖЕН если:
- Общие знания, концепции, теория
- Математика, логика, программирование (общие вопросы)
- Творческие задачи, перевод, редактура
- Разговор, советы, объяснения

Отвечай ТОЛЬКО валидным JSON без пробелов и переносов:
{"search":true,"query":"поисковый запрос на русском или английском"}
или
{"search":false,"query":""}"""


@dataclass
class DecisionResult:
    needs_search: bool
    query: str              # Поисковый запрос (если needs_search=True)
    raw_response: str       # Сырой ответ модели (для отладки)


class SearchDecisionService:
    """
    Запускает Pass 1: короткий вызов модели для принятия решения о поиске.
    Использует суммаризатор (лёгкая модель), чтобы не занимать основную.
    """

    def __init__(self, config: dict):
        self.config = config
        self.decision_config = config.get("decision", {})
        self._logger = None
        
    @property
    def logger(self):
        if self._logger is None:
            from container import container
            self._logger = container.get_logger()
        return self._logger

    async def should_search(self, user_prompt: str) -> DecisionResult:
        """
        Возвращает DecisionResult. При любой ошибке возвращает
        needs_search=False (fail-safe: лучше ответить без поиска,
        чем упасть).
        """
        try:
            return await self._run_decision(user_prompt)
        except Exception:
            return DecisionResult(
                needs_search=False,
                query="",
                raw_response="error"
            )

    async def _run_decision(self, user_prompt: str) -> DecisionResult:
        from services.context.summarizer_factory import SummarizerFactory

        context_config = self._get_context_config()
        summarizers = SummarizerFactory.get_all_summarizers(context_config)
        model = summarizers["l1"]

        user_msg = f"Запрос пользователя: {user_prompt[:500]}"

        try:
            current_datetime = _get_current_datetime_str()
            system_prompt_with_date = f"Текущая дата и время: {current_datetime}. {DECISION_SYSTEM_PROMPT}"
            result = await model.summarize(
                text=user_msg,
                system_prompt=system_prompt_with_date,
                user_prompt=user_msg,
                max_tokens=self.decision_config.get("max_tokens", 150),
                temperature=self.decision_config.get("temperature", 0.1),
                enable_thinking=False,
            )

            self.logger.info(f"🔍 [Pass 1] summarize result: success={result.success}, error={result.error}")

            if result.success:
                raw = result.summary.strip()
                self.logger.info(f"🔍 [Pass 1] Raw after strip: {raw}")
                return self._parse_response(raw)
            else:
                self.logger.error(f"🔍 [Pass 1] Summarization failed: {result.error}")
                return DecisionResult(needs_search=False, query="", raw_response=f"error: {result.error}")

        except Exception as e:
            self.logger.exception("🔍 [Pass 1] Exception in _run_decision")
            return DecisionResult(needs_search=False, query="", raw_response="error")

    def _parse_response(self, raw: str) -> DecisionResult:
        # Удаляем возможный префикс [L1 Summary]
        raw = re.sub(r'^\[L1\s*Summary\]\s*', '', raw.strip())
        # Ищем JSON-блок
        match = re.search(r'\{[^{}]+\}', raw)
        if not match:
            self.logger.info("🔍 [Pass 1] No JSON block found, returning needs_search=False")
            return DecisionResult(needs_search=False, query="", raw_response=raw)

        try:
            data = json.loads(match.group(0))
            needs_search = bool(data.get("search", False))
            query = str(data.get("query", "")).strip()

            if needs_search and not query:
                needs_search = False

            self.logger.info(f"🔍 [Pass 1] Parsed result: needs_search={needs_search}, query='{query}'")
            return DecisionResult(
                needs_search=needs_search,
                query=query,
                raw_response=raw,
            )
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.info(f"🔍 [Pass 1] JSON parse error: {e}, returning needs_search=False")
            return DecisionResult(needs_search=False, query="", raw_response=raw)

    def _get_context_config(self) -> dict:
        """Получает конфиг контекста для фабрики суммаризаторов."""
        from container import container
        full_config = container.get_config()
        return full_config.get("context", {})
