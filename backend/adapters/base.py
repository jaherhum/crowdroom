from abc import ABC
from typing import Any

import asyncio
import httpx


class StreamingPlatformAdapter(ABC):
    def __init__(self, cache_ttl: int = 86400, session: httpx.AsyncClient | None =
    None, rate_limit_delay: float = 0.5):
        """
        Args:
            cache_ttl: Cache TTL in seconds (default 24h).
            session: Optional shared async HTTP session. Caller owns lifecycle.
        """
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, Any]] = {}
        self._session = session or httpx.AsyncClient()

        self.rate_limit_delay = rate_limit_delay

    async def _request(self, url: str, **kwargs):
        await asyncio.sleep(self.rate_limit_delay)
        response = await self._session.get(url, **kwargs)
        response.raise_for_status()
        return await response.aread()
