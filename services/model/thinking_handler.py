# services/model/thinking_handler.py
import re

# Заголовок, который модель вставляет в начало блока размышлений
_HEADER_RE = re.compile(r'^Thinking process:\s*\n+', re.IGNORECASE)
# Нижний регистр для быстрой проверки префикса (без regex)
_HEADER_BASE = "thinking process:"

# Хранимый формат. Атрибуты:
#   t="12.3"  — время генерации блока (опционально)
#   stopped   — генерация прервана до закрывающего </think> (опционально)
_STORED_RE = re.compile(r'<think((?:\s+t="[\d.]+")?)(\s+stopped)?>(.*?)</think>', re.DOTALL)


class ThinkingHandler:
    """
    Единая точка форматирования блоков размышлений Qwen3.

    Форматы данных:
      raw      — сырой вывод модели: «Thinking process:\\n\\n...\\n</think>\\n\\nОтвет»
                 (открывающий <think> не включён — он является частью промпта)
      stored   — нормализованный формат для хранения:
                   завершён:  «<think t="12.3">...</think>\\n\\nОтвет»
                   остановлен: «<think stopped>...</think>»
      ui       — HTML для отображения: заголовок + <div class="thinking">...</div>
    """

    @staticmethod
    def _remove_header(text: str) -> str:
        """Удаляет заголовок 'Thinking process:' + переносы."""
        return _HEADER_RE.sub('', text)

    @staticmethod
    def _strip_header_buffered(text: str) -> str:
        """
        Удаляет заголовок без визуального мигания (чисто функционально, без состояния).

          1. Регекс совпал → заголовок полностью получен, возвращаем текст после него.
          2. text — префикс заголовка → ещё стримится, возвращаем '' (буферизация).
          3. Иначе → обычный текст, возвращаем как есть.
        """
        stripped = _HEADER_RE.sub('', text)
        if stripped != text:
            return stripped
        lower = text.lower()
        if _HEADER_BASE.startswith(lower) or lower.startswith(_HEADER_BASE):
            return ''
        return text

    _ICON = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" class="lucide lucide-atom">'
        '<g transform="scale(0.834)">'
        '<circle cx="12" cy="12" r="1"/>'
        '<path d="M20.2 20.2c2.04-2.03.02-7.36-4.5-11.9-4.54-4.52-9.87-6.54-11.9-4.5-2.04 2.03-.02 7.36 4.5 11.9 4.54 4.52 9.87 6.54 11.9 4.5Z"/>'
        '<path d="M15.7 15.7c4.52-4.54 6.54-9.87 4.5-11.9-2.03-2.04-7.36-.02-11.9 4.5-4.52 4.54-6.54 9.87-4.5 11.9 2.03 2.04 7.36.02 11.9-4.5Z"/>'
        '</g>'
        '</svg>'
    )

    @classmethod
    def _render_label(cls, seconds: float = None, stopped: bool = False) -> str:
        icon = cls._ICON
        if stopped:
            return f'<p class="thinking-header-stopped">{icon}Остановлено</p>'
        if seconds is not None:
            return f'<p class="thinking-header">{icon}Думал {seconds:.1f} сек</p>'
        return f'<p class="thinking-header-processing">{icon}Глубокое мышление</p>'

    # ──────────────────────────────────────────────
    # Streaming
    # ──────────────────────────────────────────────

    @classmethod
    def format_stream_chunk(cls, acc_text: str, thinking_seconds: float = None,
                            stopped: bool = False) -> str:
        """
        Форматирует накопленный текст во время стрима (raw → ui).

        thinking_seconds:
          None  → блок ещё генерируется (или остановлен — см. stopped)
          float → блок завершён нормально
        stopped:
          True  → генерация прервана до получения </think>
        """
        label = cls._render_label(thinking_seconds, stopped)

        if '</think>' not in acc_text:
            body = cls._strip_header_buffered(acc_text)
            css = 'thinking' if stopped else 'thinking-in-progress'
            return f'{label}\n<div class="{css}">{body}</div>'

        thinking_raw, final = acc_text.split('</think>', 1)
        thinking = cls._remove_header(thinking_raw).strip('\n')
        return f'{label}\n<div class="thinking">{thinking}</div>\n\n{final.lstrip(chr(10))}'

    # ──────────────────────────────────────────────
    # Storage
    # ──────────────────────────────────────────────

    @classmethod
    def normalize_for_storage(cls, raw: str, thinking_seconds: float = None,
                               stopped: bool = False) -> str:
        """
        Нормализует сырой вывод модели для хранения (raw → stored).

        Нормальное завершение:
          «Thinking process:\\n\\n...\\n</think>\\n\\nОтвет»
              → «<think t="12.3">...</think>\\n\\nОтвет»

        Остановка до </think>:
          «Thinking process:\\n\\n...» (без </think>)
              → «<think stopped>...</think>»
        """
        if not raw:
            return raw

        if '</think>' in raw:
            thinking_raw, final = raw.split('</think>', 1)
            thinking = cls._remove_header(thinking_raw).strip('\n')
            t_attr = f' t="{thinking_seconds:.1f}"' if thinking_seconds is not None else ''
            return f'<think{t_attr}>{thinking}</think>{final}'

        if stopped:
            thinking = cls._remove_header(raw).strip('\n')
            return f'<think stopped>{thinking}</think>'

        return raw

    # ──────────────────────────────────────────────
    # UI (при загрузке из хранилища)
    # ──────────────────────────────────────────────

    @classmethod
    def format_for_ui(cls, text: str) -> str:
        """
        Конвертирует хранимый текст в HTML для отображения.

        Поддерживает четыре формата:
          <think t="12.3">  → «Думал 12.3 сек»
          <think>           → «Глубокое мышление»
          <think stopped>   → «Остановлено»
          legacy raw        → «Глубокое мышление»
        """
        if not text:
            return text

        # stored-формат
        if '<think' in text:
            def _replacer(m: re.Match) -> str:
                t_group   = m.group(1)   # ' t="12.3"' или ''
                stopped   = m.group(2)   # ' stopped'  или None
                body      = m.group(3).strip('\n')
                t_match   = re.search(r'[\d.]+', t_group) if t_group else None
                seconds   = float(t_match.group()) if t_match else None
                label     = cls._render_label(seconds, stopped=bool(stopped))
                return f'{label}\n<div class="thinking">{body}</div>'
            return _STORED_RE.sub(_replacer, text)

        # legacy raw-формат: есть </think>, но нет <think>
        if '</think>' in text:
            thinking_raw, final = text.split('</think>', 1)
            thinking = cls._remove_header(thinking_raw).strip('\n')
            label = cls._render_label(None)
            return f'{label}\n<div class="thinking">{thinking}</div>\n\n{final.lstrip(chr(10))}'

        return text