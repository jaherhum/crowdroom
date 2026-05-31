"""Spotify playback control adapter for user-scoped API calls."""

from dataclasses import dataclass

import httpx


@dataclass
class SpotifyPlaybackState:
    """Current playback state from Spotify."""

    is_playing: bool
    track_id: str | None
    progress_ms: int | None
    device_id: str | None


class SpotifyPlaybackAdapter:
    """Adapter for controlling Spotify playback via user-scoped OAuth tokens."""

    BASE_URL = "https://api.spotify.com/v1/me/player"

    def __init__(self, access_token: str) -> None:
        self._token = access_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def play(self, track_uri: str, device_id: str | None = None) -> None:
        """Start or resume playback of a track on Spotify.

        Args:
            track_uri: Spotify track URI (e.g., "spotify:track:abc123").
            device_id: Target device ID. Uses active device if None.

        Raises:
            httpx.HTTPStatusError: If Spotify rejects the request.
        """
        async with httpx.AsyncClient() as client:
            response = await client.put(
                url=self.BASE_URL + "/play",
                headers= self._headers(),
                params={"device_id": device_id} if device_id else {},
                json={"uris": [track_uri]},
            )
            response.raise_for_status()

    async def pause(self) -> None:
        """Pause the user's current playback.

        Raises:
            httpx.HTTPStatusError: If Spotify rejects the request.
        """
        async with httpx.AsyncClient() as client:
            response = await client.put(
                url=self.BASE_URL + "/pause",
                headers=self._headers(),
            )
            response.raise_for_status()

    async def skip(self) -> None:
        """Skip to the next track in the user's Spotify queue.

        Raises:
            httpx.HTTPStatusError: If Spotify rejects the request.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=self.BASE_URL + "/next",
                headers=self._headers(),
            )
            response.raise_for_status()

    async def get_current_playback(self) -> SpotifyPlaybackState | None:
        """Get current playback state from Spotify.

        Returns:
            SpotifyPlaybackState if active playback, None if no active device.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=self.BASE_URL + "/currently-playing",
                headers=self._headers(),
            )
            if response.status_code == 204:
                return None
            response.raise_for_status()

        data = response.json()
        item = data.get("item")
        return SpotifyPlaybackState(
            is_playing=data.get("is_playing", False),
            track_id=item["id"] if item else None,
            progress_ms=data.get("progress_ms"),
            device_id=data.get("device", {}).get("id"),
        )
