# services/chat/operations.py
"""
Операции с состоянием (работа с диалогами, моделью)
"""
import asyncio
import threading
from typing import AsyncGenerator, Optional, Dict, Any, List, Tuple
from container import container


class ChatOperations:
    """Операции с состоянием"""
    
    def __init__(self):
        self._services = {}
    
    def _get_service(self, name):
        """Ленивая загрузка сервиса"""
        if name not in self._services:
            self._services[name] = container.get(name)
        return self._services[name]
    
    @property
    def dialog_service(self):
        return self._get_service("dialog_service")
    
    @property
    def model_service(self):
        return self._get_service("model_service")
    
    @property
    def config_service(self):
        return self._get_service("config_service")
    
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        stop_event: Optional[threading.Event] = None
    ) -> AsyncGenerator[str, None]:  # Изменено: теперь только строка
        """Прокси-метод для stream_response модели."""
        async for chunk in self.model_service.stream_response(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            enable_thinking=enable_thinking,
            stop_event=stop_event
        ):
            yield chunk
    
    # Конфигурация
    def get_config(self) -> Dict[str, Any]:
        """Получает конфигурацию"""
        return self.config_service.get_config()