# services/model/thinking_handler.py
import re

from markdown_it import MarkdownIt

_HEADER_RE = re.compile(r'^Thinking process:\s*\n+', re.IGNORECASE)
_HEADER_BASE = "thinking process:"
_STORED_RE = re.compile(r'<think((?:\s+t="[\d.]+")?)(\s+stopped)?>(.*?)</think>', re.DOTALL)

# Один экземпляр на модуль — потокобезопасен для чтения
_MD = MarkdownIt()


class ThinkingHandler:
    """
    Единая точка форматирования блоков размышлений Qwen3.

    Форматы данных:
      raw      — сырой вывод модели: «Thinking process:\\n\\n...\\n</think>\\n\\nОтвет»
      stored   — нормализованный формат для хранения: «<think t="12.3">...</think>\\n\\nОтвет»
      ui       — HTML для отображения
    """

    @staticmethod
    def _remove_header(text: str) -> str:
        return _HEADER_RE.sub('', text)

    @staticmethod
    def _strip_header_buffered(text: str) -> str:
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

    _CHEVRON = (
        '<span class="thinking-chevron">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
        'stroke-linejoin="round">'
        '<path d="m6 9 6 6 6-6"/>'
        '</svg>'
        '</span>'
    )

    @staticmethod
    def _normalize_thinking_body(body: str) -> str:
        """Сворачивает 2+ подряд идущих \\n в один перед рендерингом.

        Пустые строки между пунктами создают loose list → каждый <li>
        оборачивается в <p> с CSS margin → лишние визуальные отступы.
        Tight список (один \\n между пунктами) сохраняет bold и вложенные списки.
        """
        return re.sub(r'\n{2,}', '\n', body).lstrip('\n')

    @staticmethod
    def _render_body(body: str) -> str:
        """Конвертирует markdown тела thinking-блока в HTML через markdown_it.

        Пре-рендеринг в Python позволяет вставлять готовый HTML напрямую в div
        без \\n\\n перед контентом (трюк с HTML-блоком типа 6 больше не нужен).
        Текстовые узлы с лишними переносами внутри div не образуются.
        markdown_it является зависимостью Gradio и гарантированно доступна.

        После рендеринга применяется та же нормализация переносов, что и для
        основной части сообщения: три и более \\n подряд сворачиваются в два.
        """
        rendered = _MD.render(body)
        # markdown_it ставит \n между каждым тегом для читаемости HTML.
        # В div с white-space:pre-wrap эти \n — видимые текстовые узлы.
        # Убираем \n между закрывающим и открывающим тегами (браузеру они не нужны),
        # и стрипаем ведущие/хвостовые \n у всего блока.
        return re.sub(r'>\n+<', '><', rendered).strip('\n')

    @classmethod
    def _render_label(cls, seconds: float = None, stopped: bool = False) -> str:
        icon = cls._ICON
        chevron = cls._CHEVRON
        if stopped:
            return f'<p class="thinking-header-stopped">{icon}Остановлено{chevron}</p>'
        if seconds is not None:
            return f'<p class="thinking-header">{icon}Думал {seconds:.1f} сек{chevron}</p>'
        return f'<p class="thinking-header-processing">{icon}Глубокое мышление{chevron}</p>'

    # ──────────────────────────────────────────────
    # Streaming
    # ──────────────────────────────────────────────

    @classmethod
    def format_stream_chunk(cls, acc_text: str, thinking_seconds: float = None,
                            stopped: bool = False) -> str:
        label = cls._render_label(thinking_seconds, stopped)

        if '</think>' not in acc_text:
            body = cls._render_body(
                cls._normalize_thinking_body(cls._strip_header_buffered(acc_text))
            )
            css = 'thinking' if stopped else 'thinking-in-progress'
            extra = ' thinking-done' if stopped else ''
            return (
                f'<div class="thinking-block{extra}">'
                f'{label}\n<div class="{css}">{body}</div>'
                f'</div>\n\n'
            )

        thinking_raw, final = acc_text.split('</think>', 1)
        thinking = cls._render_body(
            cls._normalize_thinking_body(
                cls._remove_header(thinking_raw).strip('\n')
            )
        )
        return (
            f'<div class="thinking-block thinking-done">'
            f'{label}\n<div class="thinking">{thinking}</div>'
            f'</div>\n\n{final.lstrip(chr(10))}'
        )

    # ──────────────────────────────────────────────
    # Storage
    # ──────────────────────────────────────────────

    @classmethod
    def normalize_for_storage(cls, raw: str, thinking_seconds: float = None,
                               stopped: bool = False) -> str:
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
        Конвертирует хранимый текст в HTML.
        Все блоки получают класс thinking-done → CSS скрывает тело при холодном открытии.
        """
        if not text:
            return text

        if '<think' in text:
            def _replacer(m: re.Match) -> str:
                t_group = m.group(1)
                stopped = m.group(2)
                body    = cls._render_body(
                    cls._normalize_thinking_body(m.group(3).strip('\n'))
                )
                t_match = re.search(r'[\d.]+', t_group) if t_group else None
                seconds = float(t_match.group()) if t_match else None
                label   = cls._render_label(seconds, stopped=bool(stopped))
                return (
                    f'<div class="thinking-block thinking-done">'
                    f'{label}\n<div class="thinking">{body}</div>'
                    f'</div>\n\n'
                )
            return _STORED_RE.sub(_replacer, text)

        if '</think>' in text:
            thinking_raw, final = text.split('</think>', 1)
            thinking = cls._render_body(
                cls._normalize_thinking_body(
                    cls._remove_header(thinking_raw).strip('\n')
                )
            )
            label = cls._render_label(None)
            return (
                f'<div class="thinking-block thinking-done">'
                f'{label}\n<div class="thinking">{thinking}</div>'
                f'</div>\n\n{final.lstrip(chr(10))}'
            )

        return text