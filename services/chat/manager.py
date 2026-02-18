# services/chat/manager.py
"""
Главный менеджер для координации всех компонентов чата.
"""
import threading
from typing import AsyncGenerator, List, Dict, Optional, Tuple

from services.chat.operations import ChatOperations
from services.chat.stream_processor import MessageStreamProcessor


class ChatManager:
    """Главный менеджер для работы с чатом."""

    def __init__(self):
        self.operations = ChatOperations()
        self._stream_processor = None

    @property
    def stream_processor(self) -> MessageStreamProcessor:
        """Ленивая инициализация процессора."""
        if self._stream_processor is None:
            config = self.operations.get_config()
            self._stream_processor = MessageStreamProcessor(config, self.operations)
        return self._stream_processor

    async def process_message_stream(
        self,
        prompt: str,
        dialog_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        stop_event: Optional[threading.Event] = None,
        search_enabled: bool = False,          # ← новый параметр
    ) -> AsyncGenerator[Tuple[List[Dict], str, str, str, str], None]:
        """
        Асинхронно обрабатывает сообщение и возвращает поток обновлений.
        """
        async for result in self.stream_processor.process(
            prompt=prompt,
            dialog_id=dialog_id,
            max_tokens=max_tokens,
            temperature=temperature,
            enable_thinking=enable_thinking,
            stop_event=stop_event,
            search_enabled=search_enabled,     # ← передаём дальше
        ):
            yield result
