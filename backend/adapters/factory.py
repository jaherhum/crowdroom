from adapters.base import BaseAdapter
from adapters.spotify_search_adapter import SpotifySearchAdapter
from db.models import StreamingPlatforms


class AdapterFactory:

    @staticmethod
    def create(platform: StreamingPlatforms, credentials: dict[str, str]) -> BaseAdapter:
        if platform == StreamingPlatforms.SPOTIFY:
            return SpotifySearchAdapter(credentials)
        raise ValueError(f"Unsupported platform: {platform}")