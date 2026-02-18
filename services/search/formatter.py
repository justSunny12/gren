# services/search/formatter.py
"""
Форматирует результаты поиска в строку контекста для Pass 2.

Задача: модель должна легко разобрать источники и их содержимое,
при этом суммарный объём не должен перегружать prefill.
"""
from typing import List
from .client import SearchResult


def format_results_for_model(
    results: List[SearchResult],
    query: str,
    max_content_chars: int = 1500,
    max_total_chars: int = 5000,
) -> str:
    """
    Возвращает строку, которая добавляется в системный промпт Pass 2.

    Формат намеренно простой и явный — модели легче читать
    структуру с метками, чем markdown-таблицы.
    """
    if not results:
        return ""

    lines = [
        f'[Результаты веб-поиска по запросу: "{query}"]',
        f'[Найдено источников: {len(results)}. Используй эти данные при ответе.',
        f' Ссылайся на источники по номеру, например: [1], [2].]',
        "",
    ]

    total_chars = 0
    for i, r in enumerate(results, 1):
        # Обрезаем контент одного результата
        content = r.content.strip()
        if len(content) > max_content_chars:
            content = content[:max_content_chars] + "..."

        block = [
            f"[{i}] {r.title}",
            f"    URL: {r.url}",
        ]
        if r.published_date:
            block.append(f"    Дата: {r.published_date}")
        block.append(f"    {content}")
        block.append("")

        block_text = "\n".join(block)

        # Не превышаем суммарный лимит
        if total_chars + len(block_text) > max_total_chars:
            lines.append(f"[{i}] ... (результат пропущен: превышен лимит контекста)")
            break

        lines.append(block_text)
        total_chars += len(block_text)

    return "\n".join(lines)


def build_augmented_messages(
    original_messages: List[dict],
    search_context: str,
) -> List[dict]:
    """
    Вставляет результаты поиска как системное сообщение перед последним
    user-сообщением. Исходный список не мутируется.

    Структура:
        [...история..., system(search_context), user(последний промпт)]
    """
    if not search_context or not original_messages:
        return original_messages

    messages = list(original_messages)

    # Отделяем последнее user-сообщение
    last_user_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break

    if last_user_idx is None:
        return messages

    search_system_msg = {
        "role": "system",
        "content": search_context,
    }

    # Вставляем system-сообщение непосредственно перед последним user
    messages.insert(last_user_idx, search_system_msg)
    return messages
