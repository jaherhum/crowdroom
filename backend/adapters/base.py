import time
from abc import ABC, abstractmethod
from typing import Any

import asyncio
import httpx

from schemas.song_metadata import ReadSongMetadata


class StreamingPlatformAdapter(ABC):
    _default_headers: dict[str, str] = {}

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

    @abstractmethod
    async def search(self, isrc: str | None, query: str) -> list[ReadSongMetadata]:
        pass

    @abstractmethod
    async def get_metadata(self, external_id: str) -> ReadSongMetadata | None:
        pass

    @abstractmethod
    async def get_track_uri(self, external_id: str) -> str | None:
        pass

    async def _request(self, url: str, **kwargs):
        await asyncio.sleep(self.rate_limit_delay)
        response = await self._session.get(url, headers=self._default_headers, **kwargs)
        response.raise_for_status()
        return await response.aread()

    async def _cached_request(self, key: str, url: str, **kwargs):
        entry = self._cache.get(key)
        if entry is not None:
            expires_at, data = entry
            if time.time() < expires_at:
                return data
        expires_at = time.time() + self.cache_ttl
        req = self._request(url, **kwargs)
        data = await req
        self._cache[key] = (expires_at, data)
        return data


