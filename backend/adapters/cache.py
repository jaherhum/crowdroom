from abc import ABC, abstractmethod
import time


class PlatformCache(ABC):
    @abstractmethod
    async def get(self, key: str):
        ...
    @abstractmethod
    async def set(self, key: str, value):
        ...


class InMemoryCache(PlatformCache):
    def __init__(self, ttl: int = 86400):
        self.ttl = ttl
        self._data: dict[str, tuple[float, any]] = {}

    async def get(self, key: str):
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            del self._data[key]
            return None
        return value

    async def set(self, key: str, value):
         self._data[key] = (time.time() + self.ttl, value)