"""Factory for creating streaming platform adapter instances."""

from backend.adapters.base import BaseAdapter
from backend.adapters.spotify_search_adapter import SpotifySearchAdapter
from backend.db.models import StreamingPlatforms


class AdapterFactory:
    """Maps platform enums to concrete adapter instances."""

    @staticmethod
    def create(
        platform: StreamingPlatforms, credentials: dict[str, str]
    ) -> BaseAdapter:
        """Create an adapter for the given platform.

        Args:
            platform: Target streaming platform enum value.
            credentials: Decrypted platform credentials dict.

        Returns:
            Configured adapter instance.

        Raises:
            ValueError: If platform is not supported.
        """
        if platform == StreamingPlatforms.SPOTIFY:
            return SpotifySearchAdapter(credentials)
        raise ValueError(f"Unsupported platform: {platform}")
