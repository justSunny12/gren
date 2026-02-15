# services/chat/naming_service.py
"""
Сервис для генерации названий чатов с использованием L2 суммаризатора.
"""
import re
from typing import Optional

class ChatNamingService:
    """Генерация названий диалогов на основе первого взаимодействия."""

    def __init__(self, config: dict):
        self.config = config
        self.naming_config = config.get("chat_naming", {})

    async def generate_name(self, user_message: str, assistant_message: str) -> Optional[str]:
        """Асинхронно генерирует название чата."""
        if not self.naming_config.get("enabled", True):
            return None

        max_length = self.naming_config.get("max_name_length", 50)

        from services.context.summarizer_factory import SummarizerFactory
        summarizers = SummarizerFactory.get_all_summarizers(
            self.config.get("context", {})
        )
        l2_summarizer = summarizers["l2"]

        interaction_text = (
            f"Пользователь: {user_message}\n"
            f"Ассистент: {assistant_message}"
        )

        system_prompt = self.naming_config.get("system_prompt")
        user_prompt = f"Диалог:\n{interaction_text}\n\nКраткое название:"

        result = await l2_summarizer.summarize(
            interaction_text,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=self.naming_config.get("max_tokens", 50),
            temperature=self.naming_config.get("temperature", 0.3),
            top_p=self.naming_config.get("top_p", 0.9),
            top_k=self.naming_config.get("top_k", 40),
            repetition_penalty=self.naming_config.get("repetition_penalty", 1.1)
        )

        if not result.success:
            return None

        # Постобработка
        name = result.summary.strip()
        if '\n' in name:
            name = name.split('\n', 1)[0].strip()
        name = re.sub(r'^(название|title|name|ответ|answer|assistant|ai):\s*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^\[L[12]\s*Summary\]\s*', '', name)
        name = name.strip('"\'`').strip()
        if len(name) > max_length:
            name = name[:max_length-3] + "..."
        name = " ".join(name.splitlines())

        return name if name else None