# services/model/thinking_handler.py
import re

# Заголовок, который модель вставляет в начало блока размышлений
_HEADER_RE = re.compile(r'^Thinking process:\s*\n+', re.IGNORECASE)
# Нижний регистр для быстрой проверки префикса (без regex)
_HEADER_BASE = "thinking process:"

# Паттерн для хранимого формата: <think>...</think>
_STORED_RE = re.compile(r'<think>(.*?)</think>', re.DOTALL)


class ThinkingHandler:
    """
    Единая точка форматирования блоков размышлений Qwen3.

    Форматы данных:
      raw      — сырой вывод модели: «Thinking process:\\n\\n...\\n</think>\\n\\nОтвет»
                 (открывающий <think> не включён — он является частью промпта)
      stored   — нормализованный формат для хранения: «<think>...</think>\\n\\nОтвет»
      ui       — HTML для отображения: «<div class="thinking">...</div>\\n\\nОтвет»
    """

    @staticmethod
    def _remove_header(text: str) -> str:
        """Удаляет заголовок 'Thinking process:' + переносы. Текст уже точно содержит заголовок."""
        return _HEADER_RE.sub('', text)

    @staticmethod
    def _strip_header_buffered(text: str) -> str:
        """
        Удаляет заголовок без визуального мигания.

        Логика (чисто функциональная, без состояния):
          1. Регекс совпал → заголовок полностью получен, возвращаем текст после него.
          2. text — префикс заголовка («T», «Thi», «Thinking process:») →
             заголовок ещё стримится, возвращаем «», подавляя вывод.
          3. Иначе → обычный текст, возвращаем как есть.
        """
        stripped = _HEADER_RE.sub('', text)
        if stripped != text:                          # случай 1: заголовок удалён
            return stripped
        lower = text.lower()
        if _HEADER_BASE.startswith(lower) or lower.startswith(_HEADER_BASE):  # случай 2: буферизация
            return ''
        return text                                   # случай 3: обычный текст

    # ──────────────────────────────────────────────
    # Streaming
    # ──────────────────────────────────────────────

    @classmethod
    def format_stream_chunk(cls, acc_text: str) -> str:
        """
        Форматирует накопленный текст во время стрима (raw → ui).

        Пока </think> не получен — оборачивает в thinking-in-progress,
        подавляя заголовок «Thinking process:» до его полного получения.
        После получения </think> — финализирует блок.
        """
        if '</think>' not in acc_text:
            return f'<div class="thinking-in-progress">{cls._strip_header_buffered(acc_text)}</div>'

        thinking_raw, final = acc_text.split('</think>', 1)
        thinking = cls._remove_header(thinking_raw).strip('\n')
        return f'<div class="thinking">{thinking}</div>\n\n{final.lstrip(chr(10))}'

    # ──────────────────────────────────────────────
    # Storage
    # ──────────────────────────────────────────────

    @classmethod
    def normalize_for_storage(cls, raw: str) -> str:
        """
        Нормализует сырой вывод модели для хранения (raw → stored).

        «Thinking process:\\n\\n...\\n</think>\\n\\nОтвет»
            → «<think>...</think>\\n\\nОтвет»
        """
        if not raw or '</think>' not in raw:
            return raw

        thinking_raw, final = raw.split('</think>', 1)
        thinking = cls._remove_header(thinking_raw).strip('\n')
        return f'<think>{thinking}</think>{final}'

    # ──────────────────────────────────────────────
    # UI (при загрузке из хранилища)
    # ──────────────────────────────────────────────

    @classmethod
    def format_for_ui(cls, text: str) -> str:
        """
        Конвертирует хранимый формат в HTML для отображения (stored → ui).

        «<think>...</think>\\n\\nОтвет»
            → «<div class="thinking">...</div>\\n\\nОтвет»
        """
        if not text:
            return text
        return _STORED_RE.sub(
            lambda m: f'<div class="thinking">{m.group(1).strip(chr(10))}</div>',
            text,
        )