"""Service for handling music-related operations."""

from uuid import UUID

from backend.adapters.base import BaseAdapter
from backend.adapters.factory import AdapterFactory
from backend.repositories.room_repo import RoomRepository
from backend.repositories.session_repo import SessionRepository
from backend.schemas.song_metadata import ReadSongMetadata
from backend.services.platform_connection_service import PlatformConnectionService


class MusicService:
    """Orchestrates music operations by resolving room credentials to adapters."""

    def __init__(
        self,
        platform_connection_service: PlatformConnectionService,
        room_repo: RoomRepository,
        session_repo: SessionRepository,
    ) -> None:
        self._platform_connection_service = platform_connection_service
        self._room_repo = room_repo
        self._session_repo = session_repo

    def _get_adapter(self, room_id: UUID) -> BaseAdapter:
        """Resolve room to its host's configured adapter.

        Args:
            room_id: UUID of the room whose host credentials to use.

        Returns:
            Configured adapter for the session's current platform.
        """
        session = self._session_repo.get_by_id(room_id)
        room = self._room_repo.get_by_id(room_id)
        credentials = self._platform_connection_service.get_decrypted_credentials(
            room.host_user_id, session.current_platform
        )
        adapter = AdapterFactory.create(session.current_platform, credentials)
        return adapter

    async def search(self, room_id: UUID, query: str) -> list[ReadSongMetadata]:
        """Search for tracks using the room's configured platform.

        Args:
            room_id: UUID of the room providing host credentials.
            query: Free-text search string.

        Returns:
            List of matching tracks.
        """
        adapter = self._get_adapter(room_id)
        return await adapter.search(query)

    async def get_metadata(
        self, room_id: UUID, external_id: str
    ) -> ReadSongMetadata | None:
        """Retrieve track metadata via the room's platform adapter.

        Args:
            room_id: UUID of the room providing host credentials.
            external_id: Platform-specific track identifier.

        Returns:
            Track metadata if found, None otherwise.
        """
        adapter = self._get_adapter(room_id)
        return await adapter.get_metadata(external_id)

    async def get_track_uri(self, room_id: UUID, external_id: str) -> str | None:
        """Resolve a track's playback URI via the room's platform adapter.

        Args:
            room_id: UUID of the room providing host credentials.
            external_id: Platform-specific track identifier.

        Returns:
            Playback URI string if resolvable, None otherwise.
        """
        adapter = self._get_adapter(room_id)
        return await adapter.get_track_uri(external_id)
