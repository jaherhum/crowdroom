"""Spotify credential validation adapter."""

from backend.adapters.spotify_utils import request_token


class SpotifyAuthAdapter:
    """Validates Spotify credentials by attempting Client Credentials Flow."""

    @staticmethod
    async def validate_credentials(credentials: dict[str, str]) -> None:
        """Raise InvalidPlatformCredentialsException if credentials are invalid."""
        await request_token(credentials)
