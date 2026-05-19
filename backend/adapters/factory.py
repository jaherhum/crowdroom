from backend.adapters.base import BaseAdapter
from backend.adapters.spotify_search_adapter import SpotifySearchAdapter
from backend.db.models import StreamingPlatforms


class AdapterFactory:

    @staticmethod
    def create(platform: StreamingPlatforms, credentials: dict[str, str]) -> BaseAdapter:
        if platform == StreamingPlatforms.SPOTIFY:
            return SpotifySearchAdapter(credentials)
        raise ValueError(f"Unsupported platform: {platform}")