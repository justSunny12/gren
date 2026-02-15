# services/model/thinking_handler.py
import re

class ThinkingHandler:
    """Обработчик тегов размышлений <think>."""

    @staticmethod
    def format_think_markdown(text: str) -> str:
        """
        Заменяет <think> на '<div class="thinking">', а </think> на '</div>' в потоке.
        Удаляет все переносы строк сразу после открывающего тега.
        """
        if not text:
            return text
        result = []
        i = 0
        n = len(text)
        while i < n:
            if text.startswith('<think>', i):
                result.append('<div class="thinking">')
                i += 7
                # Удаляем все последующие переносы строк
                while i < n and text[i] == '\n':
                    i += 1
            elif text.startswith('</think>', i):
                result.append('</div>')
                i += 8
            else:
                result.append(text[i])
                i += 1
        return ''.join(result)

    @staticmethod
    def clean_think_block(text: str) -> str:
        """
        Удаляет последний перенос строки перед закрывающим тегом </div> в блоке .thinking.
        Применяется после завершения генерации.
        """
        if not text:
            return text
        # Ищем блок .thinking, который заканчивается на \n</div>
        pattern = r'(<div class="thinking">.*?)\n(</div>)'
        return re.sub(pattern, r'\1\2', text, flags=re.DOTALL)