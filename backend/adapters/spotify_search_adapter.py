"""Spotify search adapter."""

import time
from typing import ClassVar

import httpx

from backend.adapters.base import BaseAdapter
from backend.adapters.spotify_utils import request_token
from backend.db.models.enum import StreamingPlatforms
from backend.schemas.song_metadata import ReadSongMetadata


class SpotifySearchAdapter(BaseAdapter):
    """Adapter for searching and retrieving track metadata from Spotify."""

    REQUIRED_CREDENTIALS: ClassVar[set[str]] = {"client_id", "client_secret"}

    def __init__(self, credentials: dict[str, str]) -> None:
        missing = self.REQUIRED_CREDENTIALS - credentials.keys()
        if missing:
            raise ValueError(f"Missing required credentials: {missing}")

        self._client_id = credentials["client_id"]
        self._client_secret = credentials["client_secret"]
        self._token: str | None = None
        self._token_expiry: float = 0

    async def _get_access_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token

        data = await request_token({
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        })

        self._token = data["access_token"]
        self._token_expiry = time.time() + data["expires_in"] - 60
        return self._token

    async def search(self, query: str | None = None) -> list[ReadSongMetadata]:
        if not query:
            return []

        token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.spotify.com/v1/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": query, "type": "track", "limit": 10},
            )

        if response.status_code != 200:
            return []

        tracks = response.json().get("tracks", {}).get("items", [])
        return [self._map_track(track) for track in tracks]

    async def get_metadata(self, external_id: str) -> ReadSongMetadata | None:
        token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.spotify.com/v1/tracks/{external_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

        if response.status_code != 200:
            return None

        return self._map_track(response.json())

    async def get_track_uri(self, external_id: str) -> str | None:
        return f"spotify:track:{external_id}"

    @staticmethod
    def _map_track(track: dict) -> ReadSongMetadata:
        images = track.get("album", {}).get("images", [])
        return ReadSongMetadata(
            title=track["name"],
            artist=track["artists"][0]["name"],
            artists=[a["name"] for a in track["artists"]],
            album=track.get("album", {}).get("name", ""),
            duration_ms=track.get("duration_ms"),
            is_explicit=track.get("explicit", False),
            album_art_url=images[0]["url"] if images else None,
            platform=StreamingPlatforms.SPOTIFY,
            external_id=track["id"],
            isrc=track.get("external_ids", {}).get("isrc"),
        )
