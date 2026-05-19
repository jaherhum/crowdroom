"""Service for handling music-related operations."""
from uuid import UUID

from backend.adapters.factory import AdapterFactory
from backend.repositories.room_repo import RoomRepository
from backend.repositories.session_repo import SessionRepository
from backend.schemas.song_metadata import ReadSongMetadata
from backend.services.platform_connection_service import PlatformConnectionService


class MusicService:
    def __init__(self,
                 platform_connection_service: PlatformConnectionService,
                 room_repo: RoomRepository,
                 session_repo: SessionRepository) -> None:
        self._platform_connection_service = platform_connection_service
        self._room_repo = room_repo
        self._session_repo = session_repo

    async def search(self, room_id: UUID, query: str) -> list[ReadSongMetadata]:
        session = self._session_repo.get_by_id(room_id)
        room = self._room_repo.get_by_id(room_id)
        credentials = self._platform_connection_service.get_decrypted_credentials(room.host_user_id, session.current_platform)
        adapter = AdapterFactory.create(session.current_platform, credentials)
        return await adapter.search(query)

