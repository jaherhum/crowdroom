"""Service for managing user platform connections."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from backend.adapters.spotify_auth_adapter import SpotifyAuthAdapter
from backend.core.encryption import decrypt_data, encrypt_data
from backend.core.exceptions import EntityNotFoundException
from backend.db.models import PlatformConnection, StreamingPlatforms
from backend.db.models.enum import ConnectionType
from backend.repositories.platform_connection_repo import PlatformConnectionRepo
from backend.schemas.platform_connection import (
    CreatePlatformConnection,
    StoreOAuthTokens,
)


class PlatformConnectionService:
    """Manages lifecycle of user-to-platform credential connections."""

    def __init__(self, repo: PlatformConnectionRepo):
        self._repo = repo

    async def connect(
        self, user_id: UUID, data: CreatePlatformConnection
    ) -> PlatformConnection:
        """Validate and store platform credentials for a user.

        Upserts: if a connection already exists for this user+platform,
        updates its credentials. Otherwise creates a new one.

        Args:
            user_id: UUID of the user connecting their account.
            data: Platform type and raw credentials to store.

        Returns:
            Created or updated PlatformConnection record.

        Raises:
            InvalidPlatformCredentialsException: If platform rejects credentials.
        """
        await SpotifyAuthAdapter.validate_credentials(data.credentials)

        existing = self._repo.get_by_user_and_platform(user_id, data.platform)
        if existing:
            existing.credentials_encrypted = encrypt_data(data.credentials)
            return self._repo.update(existing)

        connection = PlatformConnection(
            user_id=user_id,
            platform=data.platform,
            credentials_encrypted=encrypt_data(data.credentials),
        )
        return self._repo.create(connection)

    def get_spotify_app_credentials(self, user_id: UUID) -> dict[str, str] | None:
        """Return decrypted Spotify app credentials (client_id/secret) for user.

        Args:
            user_id: UUID of the user.

        Returns:
            Dict with client_id and client_secret, or None if not stored.
        """
        connection = self._repo.get_by_user_and_platform(
            user_id, StreamingPlatforms.SPOTIFY
        )
        if not connection or not connection.credentials_encrypted:
            return None
        return decrypt_data(connection.credentials_encrypted)

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

    def store_oauth_tokens(
        self, user_id: UUID, platform: StreamingPlatforms, tokens: StoreOAuthTokens
    ) -> PlatformConnection:
        """Encrypt and persist OAuth tokens for an authorization code connection.

        Args:
            user_id: UUID of the user.
            platform: Target streaming platform.
            tokens: OAuth token data to store.

        Returns:
            Updated PlatformConnection record.

        Raises:
            EntityNotFoundException: If no connection exists for user+platform.
        """
        connection = self._repo.get_by_user_and_platform(user_id, platform)
        if not connection:
            connection = PlatformConnection(
                user_id=user_id,
                platform=platform,
                connection_type=ConnectionType.AUTHORIZATION_CODE,
            )

        connection.access_token_encrypted = encrypt_data(
            {"access_token": tokens.access_token}
        )
        connection.refresh_token_encrypted = encrypt_data(
            {"refresh_token": tokens.refresh_token}
        )
        connection.token_expires_at = tokens.expires_at
        connection.scopes = tokens.scopes
        connection.connection_type = ConnectionType.AUTHORIZATION_CODE

        if connection.id:
            return self._repo.update(connection)
        return self._repo.create(connection)

    async def get_valid_access_token(
        self, user_id: UUID, platform: StreamingPlatforms
    ) -> str:
        """Return a valid access token, refreshing proactively if near expiry.

        Args:
            user_id: UUID of the token owner.
            platform: Target streaming platform.

        Returns:
            Decrypted access token string.

        Raises:
            EntityNotFoundException: If no OAuth connection exists.
        """
        connection = self._repo.get_by_user_and_platform(user_id, platform)
        is_oauth = (
            connection
            and connection.connection_type == ConnectionType.AUTHORIZATION_CODE
        )
        if not is_oauth:
            raise EntityNotFoundException(
                "PlatformConnection (OAuth)", f"{user_id}:{platform.value}"
            )

        buffer = timedelta(minutes=5)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        expires_at = connection.token_expires_at
        if expires_at and expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)

        if not expires_at or expires_at - now < buffer:
            return await self._refresh_access_token(connection)

        token_data = decrypt_data(connection.access_token_encrypted)
        return token_data["access_token"]

    async def force_refresh_token(
        self, user_id: UUID, platform: StreamingPlatforms
    ) -> str:
        """Force a token refresh regardless of expiry time.

        Args:
            user_id: UUID of the token owner.
            platform: Target streaming platform.

        Returns:
            Fresh access token string.

        Raises:
            EntityNotFoundException: If no OAuth connection exists.
        """
        connection = self._repo.get_by_user_and_platform(user_id, platform)
        if not connection:
            raise EntityNotFoundException(
                "PlatformConnection (OAuth)", f"{user_id}:{platform.value}"
            )
        return await self._refresh_access_token(connection)

    def _resolve_app_credentials(
        self, connection: PlatformConnection
    ) -> tuple[str, str]:
        """Get client_id and client_secret for a connection.

        Uses per-user credentials if stored, falls back to global settings.

        Args:
            connection: The PlatformConnection to resolve credentials for.

        Returns:
            Tuple of (client_id, client_secret).
        """
        from backend.core.config import settings

        if connection.credentials_encrypted:
            creds = decrypt_data(connection.credentials_encrypted)
            if creds.get("client_id") and creds.get("client_secret"):
                return creds["client_id"], creds["client_secret"]
        return settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET

    async def _refresh_access_token(self, connection: PlatformConnection) -> str:
        """Refresh an expired OAuth access token via Spotify's token endpoint.

        Uses per-user app credentials if available, falls back to settings.

        Args:
            connection: PlatformConnection with refresh token stored.

        Returns:
            New decrypted access token string.

        Raises:
            InvalidPlatformCredentialsException: If refresh token is revoked.
        """
        from backend.core.exceptions import InvalidPlatformCredentialsException

        refresh_data = decrypt_data(connection.refresh_token_encrypted)
        refresh_token = refresh_data["refresh_token"]
        client_id, client_secret = self._resolve_app_credentials(connection)

        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url="https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            if response.status_code in (400, 401):
                raise InvalidPlatformCredentialsException(
                    "Spotify refresh token revoked. Please reconnect."
                )
            response.raise_for_status()
            token_response = response.json()

        new_access_token = token_response["access_token"]
        expires_in = token_response["expires_in"]

        connection.access_token_encrypted = encrypt_data(
            {"access_token": new_access_token}
        )
        connection.token_expires_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(seconds=expires_in)

        if "refresh_token" in token_response:
            connection.refresh_token_encrypted = encrypt_data(
                {"refresh_token": token_response["refresh_token"]}
            )

        self._repo.update(connection)
        return new_access_token

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
