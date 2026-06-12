"""Tests for metadata TTL cache module."""

# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest

from backend.adapters.cache import (
    clear_cache,
    get_cached_metadata,
    set_cached_metadata,
)
from backend.adapters.spotify_search_adapter import SpotifySearchAdapter
from backend.db.models.enum import StreamingPlatforms
from backend.schemas.song_metadata import ReadSongMetadata


@pytest.fixture(autouse=True)
def _clean_cache():
    """Clear cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


def _make_metadata(external_id: str = "track1") -> ReadSongMetadata:
    return ReadSongMetadata(
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration_ms=200000,
        isrc=None,
        platform=StreamingPlatforms.SPOTIFY,
        album_art_url=None,
        artists=["Test Artist"],
        is_explicit=False,
        external_id=external_id,
    )


class TestCacheGetSet:
    def test_get_returns_none_on_miss(self):
        result = get_cached_metadata("spotify", "nonexistent")
        assert result is None

    def test_set_then_get_returns_value(self):
        metadata = _make_metadata("abc")
        set_cached_metadata("spotify", "abc", metadata)
        result = get_cached_metadata("spotify", "abc")
        assert result is not None
        assert result.external_id == "abc"
        assert result.title == "Test Song"

    @pytest.mark.skip(reason="Tidal pending implementation; re-enable with adapter")
    def test_different_platforms_cached_separately(self):
        meta_spotify = _make_metadata("same_id")
        meta_tidal = ReadSongMetadata(
            title="Tidal Version",
            artist="Artist",
            album="Album",
            duration_ms=200000,
            isrc=None,
            platform=StreamingPlatforms.TIDAL,
            album_art_url=None,
            artists=["Artist"],
            is_explicit=False,
            external_id="same_id",
        )
        set_cached_metadata("spotify", "same_id", meta_spotify)
        set_cached_metadata("tidal", "same_id", meta_tidal)

        assert get_cached_metadata("spotify", "same_id").title == "Test Song"
        assert get_cached_metadata("tidal", "same_id").title == "Tidal Version"

    def test_clear_removes_all_entries(self):
        set_cached_metadata("spotify", "a", _make_metadata("a"))
        set_cached_metadata("spotify", "b", _make_metadata("b"))
        clear_cache()
        assert get_cached_metadata("spotify", "a") is None
        assert get_cached_metadata("spotify", "b") is None


class TestAdapterCacheIntegration:
    @pytest.fixture
    def adapter(self):
        return SpotifySearchAdapter({"client_id": "id", "client_secret": "secret"})

    def test_cache_hit_skips_http_call(self, adapter):
        metadata = _make_metadata("cached_track")
        set_cached_metadata(StreamingPlatforms.SPOTIFY.value, "cached_track", metadata)

        async def _run():
            return await adapter.get_metadata("cached_track")

        with patch(
            "backend.adapters.spotify_search_adapter.request_token"
        ) as mock_token:
            result = anyio.run(_run)
            mock_token.assert_not_called()

        assert result.external_id == "cached_track"

    @patch("backend.adapters.spotify_search_adapter.request_token")
    @patch("backend.adapters.spotify_search_adapter.httpx.AsyncClient")
    def test_successful_lookup_populates_cache(
        self, mock_client_cls, mock_token, adapter
    ):
        mock_token.return_value = {"access_token": "tok", "expires_in": 3600}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "new_track",
            "name": "New Song",
            "artists": [{"name": "Artist"}],
            "album": {"name": "Album", "images": []},
            "duration_ms": 180000,
            "explicit": False,
            "external_ids": {},
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await adapter.get_metadata("new_track")

        anyio.run(_run)

        cached = get_cached_metadata(StreamingPlatforms.SPOTIFY.value, "new_track")
        assert cached is not None
        assert cached.title == "New Song"

    @patch("backend.adapters.spotify_search_adapter.request_token")
    @patch("backend.adapters.spotify_search_adapter.httpx.AsyncClient")
    def test_failed_lookup_does_not_cache(self, mock_client_cls, mock_token, adapter):
        mock_token.return_value = {"access_token": "tok", "expires_in": 3600}

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await adapter.get_metadata("missing")

        result = anyio.run(_run)

        assert result is None
        assert get_cached_metadata(StreamingPlatforms.SPOTIFY.value, "missing") is None
