from abc import ABC, abstractmethod

from backend.schemas.song_metadata import ReadSongMetadata


class BaseAdapter(ABC):
    @abstractmethod
    async def search(self, query: str | None = None) -> list[ReadSongMetadata]:
        pass

    @abstractmethod
    async def get_metadata(self, external_id: str) -> ReadSongMetadata | None:
        pass

    @abstractmethod
    async def get_track_uri(self, external_id: str) -> str | None:
        pass
