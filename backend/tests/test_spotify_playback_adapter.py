"""Tests for SpotifyPlaybackAdapter."""

# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest

from backend.adapters.spotify_playback_adapter import (
    SpotifyPlaybackAdapter,
    SpotifyPlaybackState,
)


class TestSpotifyPlaybackAdapterPlay:
    @pytest.fixture
    def adapter(self):
        return SpotifyPlaybackAdapter("test_token")

    @patch("backend.adapters.spotify_playback_adapter.httpx.AsyncClient")
    def test_play_sends_put_with_uri(self, mock_client_cls, adapter):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            await adapter.play("spotify:track:abc123")

        anyio.run(_run)

        mock_client.put.assert_called_once_with(
            url="https://api.spotify.com/v1/me/player/play",
            headers={"Authorization": "Bearer test_token"},
            params={},
            json={"uris": ["spotify:track:abc123"]},
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("backend.adapters.spotify_playback_adapter.httpx.AsyncClient")
    def test_play_with_device_id(self, mock_client_cls, adapter):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            await adapter.play("spotify:track:abc123", device_id="device1")

        anyio.run(_run)

        mock_client.put.assert_called_once_with(
            url="https://api.spotify.com/v1/me/player/play",
            headers={"Authorization": "Bearer test_token"},
            params={"device_id": "device1"},
            json={"uris": ["spotify:track:abc123"]},
        )


class TestSpotifyPlaybackAdapterPause:
    @pytest.fixture
    def adapter(self):
        return SpotifyPlaybackAdapter("test_token")

    @patch("backend.adapters.spotify_playback_adapter.httpx.AsyncClient")
    def test_pause_sends_put(self, mock_client_cls, adapter):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            await adapter.pause()

        anyio.run(_run)

        mock_client.put.assert_called_once_with(
            url="https://api.spotify.com/v1/me/player/pause",
            headers={"Authorization": "Bearer test_token"},
        )
        mock_response.raise_for_status.assert_called_once()


class TestSpotifyPlaybackAdapterSkip:
    @pytest.fixture
    def adapter(self):
        return SpotifyPlaybackAdapter("test_token")

    @patch("backend.adapters.spotify_playback_adapter.httpx.AsyncClient")
    def test_skip_sends_post(self, mock_client_cls, adapter):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            await adapter.skip()

        anyio.run(_run)

        mock_client.post.assert_called_once_with(
            url="https://api.spotify.com/v1/me/player/next",
            headers={"Authorization": "Bearer test_token"},
        )
        mock_response.raise_for_status.assert_called_once()


class TestSpotifyPlaybackAdapterGetCurrentPlayback:
    @pytest.fixture
    def adapter(self):
        return SpotifyPlaybackAdapter("test_token")

    @patch("backend.adapters.spotify_playback_adapter.httpx.AsyncClient")
    def test_returns_none_on_204(self, mock_client_cls, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await adapter.get_current_playback()

        result = anyio.run(_run)
        assert result is None

    @patch("backend.adapters.spotify_playback_adapter.httpx.AsyncClient")
    def test_returns_playback_state(self, mock_client_cls, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "is_playing": True,
            "item": {"id": "track456"},
            "progress_ms": 30000,
            "device": {"id": "device789"},
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await adapter.get_current_playback()

        result = anyio.run(_run)
        assert result == SpotifyPlaybackState(
            is_playing=True,
            track_id="track456",
            progress_ms=30000,
            device_id="device789",
        )

    @patch("backend.adapters.spotify_playback_adapter.httpx.AsyncClient")
    def test_returns_none_track_when_item_is_none(self, mock_client_cls, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "is_playing": False,
            "item": None,
            "progress_ms": None,
            "device": {"id": "device789"},
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await adapter.get_current_playback()

        result = anyio.run(_run)
        assert result == SpotifyPlaybackState(
            is_playing=False,
            track_id=None,
            progress_ms=None,
            device_id="device789",
        )
