from uuid import UUID

from backend.adapters.spotify_auth_adapter import SpotifyAuthAdapter
from backend.repositories.platform_connection_repo import PlatformConnectionRepo
from backend.schemas.platform_connection import CreatePlatformConnection
from backend.db.models import PlatformConnection
from backend.core.encryption import encrypt_data, decrypt_data
from backend.core.exceptions import EntityNotFoundException
from backend.db.models import StreamingPlatforms


class PlatformConnectionService:
    def __init__(self, repo: PlatformConnectionRepo):
        self._repo = repo

    async def connect(self, user_id: UUID, data: CreatePlatformConnection) -> PlatformConnection:
        await SpotifyAuthAdapter.validate_credentials(data.credentials)
        connection = PlatformConnection(
            user_id=user_id,
            platform=data.platform,
            credentials_encrypted=encrypt_data(data.credentials),
        )
        return self._repo.create(connection)

    def get_connections(self, user_id: UUID) -> list[PlatformConnection]:
        return self._repo.get_all_by_user(user_id)

    def get_decrypted_credentials(self, user_id: UUID, platform: StreamingPlatforms) -> dict[str, str]:
        connection = self._repo.get_by_user_and_platform(user_id, platform)
        if not connection:
            raise EntityNotFoundException("PlatformConnection", f"{user_id}:{platform.value}")
        return decrypt_data(connection.credentials_encrypted)

    def disconnect(self, user_id: UUID, platform: StreamingPlatforms) -> None:
        connection = self._repo.get_by_user_and_platform(user_id, platform)
        if not connection:
            raise EntityNotFoundException("PlatformConnection", f"{user_id}:{platform.value}")
        self._repo.delete(connection.id)