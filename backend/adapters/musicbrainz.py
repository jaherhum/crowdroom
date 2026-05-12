import json
import xml.etree.ElementTree as ET

from backend.adapters.base import StreamingPlatformAdapter
from backend.core.config import settings


class MusicBrainzAdapter(StreamingPlatformAdapter):
    BASE_URL = settings.MUSICBRAINZ_API_URL
    _default_headers = {"User-Agent": "crowdroom/0.5 (https://github.com/jaherhum/crowdroom)"}

    def __init__(self, session=None, rate_limit_delay=1.0):
        super().__init__(session=session, rate_limit_delay=rate_limit_delay)

    async def search(self, query: str, limit: int = 20):
        data = await self._cached_request(
            f"search:{query}:{limit}",
            f"{self.BASE_URL}/search",
            params={"query": query, "type": "recording", "limit": limit},
        )
        return json.loads(data).get("recordings", [])

    async def get_by_mbid(self, mbid: str):
        data = await self._cached_request(
            f"mbid:{mbid}",
            f"{self.BASE_URL}/recording/{mbid}",
        )
        result = json.loads(data)
        return result if result.get("id") else None

    async def get_by_isrc(self, isrc: str):
        xml = await self._cached_request(
            f"isrc:{isrc}",
            f"{self.BASE_URL}/isrclookup/recording",
            params={"isrc": isrc},
        )
        root = ET.fromstring(xml)
        recording = root.find("recording")
        return {
            "id": recording.get("id") if recording is not None else None,
            "title": root.findtext(".//title"),
        }
