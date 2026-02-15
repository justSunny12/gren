# services/context/builder.py
"""
Построение контекста для генерации из состояния.
"""
from models.context import DialogContextState


class ContextBuilder:
    """Формирует итоговую строку контекста для передачи модели."""

    @staticmethod
    def build(state: DialogContextState, history_length: int) -> str:
        """Собирает контекст из всех уровней суммаризации."""
        if history_length < 2:
            return ""

        parts = []

        # Системное сообщение с инструкцией
        system = """Ты получаешь контекст диалога в нескольких частях:

1. <sum_block>...</sum_block> - кумулятивные суммаризации всего диалога (высший уровень обобщения)
2. ## Чанк: - конспекты групп сообщений среднего уровня детализации
3. Последние сообщения - полный текст последней части диалога (максимальная детализация)

Внимательно изучи ВЕСЬ предоставленный контекст перед ответом. Особое внимание уделяй последним сообщениям."""
        parts.append(system)

        # Кумулятивная строка
        if state.cumulative_context.content:
            parts.append(state.cumulative_context.get_formatted())

        # Чанки L1
        if state.l1_chunks:
            l1_context = "# Конспекты недавних обсуждений (средний уровень детализации):\n"
            for i, chunk in enumerate(state.l1_chunks, 1):
                l1_context += f"\n## Чанк {i}:\n{chunk.summary}\n"
            parts.append(l1_context)

        # Сырой хвост
        if state.raw_tail:
            raw_context = "# Последние сообщения (полный текст, максимальная детализация):\n"
            raw_context += state.raw_tail
            parts.append(raw_context)

        parts.append("\n" + "="*50 + "\n")
        return "\n\n".join(parts)