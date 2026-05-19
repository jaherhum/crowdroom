"""Abstract base class for streaming platform adapters."""

from abc import ABC, abstractmethod

from backend.schemas.song_metadata import ReadSongMetadata


class BaseAdapter(ABC):
    """Platform-agnostic interface for streaming service operations."""

    @abstractmethod
    async def search(self, query: str | None = None) -> list[ReadSongMetadata]:
        """Search for tracks on the streaming platform.

        Args:
            query: Free-text search string. Returns empty list if None.

        Returns:
            List of matching tracks as platform-agnostic metadata.
        """

    @abstractmethod
    async def get_metadata(self, external_id: str) -> ReadSongMetadata | None:
        """Retrieve metadata for a specific track by platform ID.

        Args:
            external_id: Platform-specific track identifier.

        Returns:
            Track metadata if found, None otherwise.
        """

    @abstractmethod
    async def get_track_uri(self, external_id: str) -> str | None:
        """Resolve a track's playback URI.

        Args:
            external_id: Platform-specific track identifier.

        Returns:
            Playback URI string if resolvable, None otherwise.
        """
