"""Service for managing user platform connections."""

from uuid import UUID

from backend.adapters.spotify_auth_adapter import SpotifyAuthAdapter
from backend.core.encryption import decrypt_data, encrypt_data
from backend.core.exceptions import EntityNotFoundException
from backend.db.models import PlatformConnection, StreamingPlatforms
from backend.repositories.platform_connection_repo import PlatformConnectionRepo
from backend.schemas.platform_connection import CreatePlatformConnection


class PlatformConnectionService:
    """Manages lifecycle of user-to-platform credential connections."""

    def __init__(self, repo: PlatformConnectionRepo):
        self._repo = repo

    async def connect(
        self, user_id: UUID, data: CreatePlatformConnection
    ) -> PlatformConnection:
        """Validate and store platform credentials for a user.

        Args:
            user_id: UUID of the user connecting their account.
            data: Platform type and raw credentials to store.

        Returns:
            Created PlatformConnection record.

        Raises:
            InvalidPlatformCredentialsException: If platform rejects credentials.
        """
        await SpotifyAuthAdapter.validate_credentials(data.credentials)
        connection = PlatformConnection(
            user_id=user_id,
            platform=data.platform,
            credentials_encrypted=encrypt_data(data.credentials),
        )
        return self._repo.create(connection)

    def get_connections(self, user_id: UUID) -> list[PlatformConnection]:
        """Retrieve all platform connections for a user.

        Args:
            user_id: UUID of the user.

        Returns:
            List of PlatformConnection records.
        """
        return self._repo.get_all_by_user(user_id)

    def get_decrypted_credentials(
        self, user_id: UUID, platform: StreamingPlatforms
    ) -> dict[str, str]:
        """Retrieve and decrypt stored credentials for a user+platform pair.

        Args:
            user_id: UUID of the credential owner.
            platform: Target streaming platform.

        Returns:
            Decrypted credentials dictionary.

        Raises:
            EntityNotFoundException: If no connection exists for user+platform.
        """
        connection = self._repo.get_by_user_and_platform(user_id, platform)
        if not connection:
            raise EntityNotFoundException(
                "PlatformConnection", f"{user_id}:{platform.value}"
            )
        return decrypt_data(connection.credentials_encrypted)

    def disconnect(self, user_id: UUID, platform: StreamingPlatforms) -> None:
        """Remove a user's connection to a platform.

        Args:
            user_id: UUID of the user.
            platform: Platform to disconnect from.

        Raises:
            EntityNotFoundException: If no connection exists for user+platform.
        """
        connection = self._repo.get_by_user_and_platform(user_id, platform)
        if not connection:
            raise EntityNotFoundException(
                "PlatformConnection", f"{user_id}:{platform.value}"
            )
        self._repo.delete(connection.id)
