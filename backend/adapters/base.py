from abc import ABC, abstractmethod

import asyncio
import httpx

from backend.adapters.cache import InMemoryCache, PlatformCache
from backend.schemas.song_metadata import ReadSongMetadata


class StreamingPlatformAdapter(ABC):
    _default_headers: dict[str, str] = {}

    def __init__(self, cache_ttl: int = 86400, session: httpx.AsyncClient | None =
    None, rate_limit_delay: float = 0.5, cache: PlatformCache | None = None):
        """
        Args:
            cache_ttl: Cache TTL in seconds (default 24h).
            session: Optional shared async HTTP session. Caller owns lifecycle.
            cache: Optional shared cache backend. Defaults to InMemoryCache(ttl=cache_ttl).
        """
        self.cache_ttl = cache_ttl
        self._cache = cache or InMemoryCache(ttl=cache_ttl)
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
        cached = await self._cache.get(key)
        if cached is not None:
            return cached

        data = await self._request(url, **kwargs)
        await self._cache.set(key, data)
        return data


