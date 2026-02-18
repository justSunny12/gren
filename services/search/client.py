# services/search/client.py
"""
Клиент для Tavily Search API.
Документация: https://docs.tavily.com/docs/python-sdk/tavily-search
"""
from dataclasses import dataclass
from typing import List, Optional
import httpx


@dataclass
class SearchResult:
    title: str
    url: str
    content: str          # Релевантный фрагмент от Tavily
    score: float          # Релевантность (0–1)
    published_date: Optional[str] = None


class TavilyClient:
    """Тонкая обёртка над Tavily REST API."""

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout

    async def search(
        self,
        query: str,
        max_results: int = 3,
        search_depth: str = "basic",
    ) -> List[SearchResult]:
        """
        Выполняет поиск и возвращает список результатов.
        Raises httpx.HTTPError при сетевых ошибках.
        """
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": False,
            "include_raw_content": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.BASE_URL, json=payload)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=item.get("score", 0.0),
                published_date=item.get("published_date"),
            ))

        return results
