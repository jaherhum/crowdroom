"""Tests for Spotify adapters (search, auth, utils)."""

# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest

from backend.adapters.spotify_auth_adapter import SpotifyAuthAdapter
from backend.adapters.spotify_search_adapter import SpotifySearchAdapter
from backend.core.exceptions import InvalidPlatformCredentialsException
from backend.db.models.enum import StreamingPlatforms


class TestSpotifySearchAdapterInit:
    def test_missing_client_id_raises(self):
        with pytest.raises(ValueError, match="client_id"):
            SpotifySearchAdapter({"client_secret": "secret"})

    def test_missing_client_secret_raises(self):
        with pytest.raises(ValueError, match="client_secret"):
            SpotifySearchAdapter({"client_id": "id"})

    def test_valid_credentials_creates_adapter(self):
        adapter = SpotifySearchAdapter({"client_id": "id", "client_secret": "secret"})
        assert adapter._client_id == "id"
        assert adapter._client_secret == "secret"


class TestSpotifySearchAdapterSearch:
    @pytest.fixture
    def adapter(self):
        return SpotifySearchAdapter({"client_id": "id", "client_secret": "secret"})

    def test_search_none_query_returns_empty(self, adapter):
        async def _run():
            return await adapter.search(None)

        result = anyio.run(_run)
        assert result == []

    def test_search_empty_query_returns_empty(self, adapter):
        async def _run():
            return await adapter.search("")

        result = anyio.run(_run)
        assert result == []

    @patch("backend.adapters.spotify_search_adapter.request_token")
    @patch("backend.adapters.spotify_search_adapter.httpx.AsyncClient")
    def test_search_returns_mapped_tracks(self, mock_client_cls, mock_token, adapter):
        mock_token.return_value = {"access_token": "tok", "expires_in": 3600}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tracks": {
                "items": [
                    {
                        "id": "track123",
                        "name": "Bohemian Rhapsody",
                        "artists": [{"name": "Queen"}],
                        "album": {"name": "A Night at the Opera", "images": [{"url": "http://img.url"}]},
                        "duration_ms": 354000,
                        "explicit": False,
                        "external_ids": {"isrc": "GBAYE7500101"},
                    }
                ]
            }
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await adapter.search("bohemian")

        results = anyio.run(_run)
        assert len(results) == 1
        assert results[0].title == "Bohemian Rhapsody"
        assert results[0].artist == "Queen"
        assert results[0].platform == StreamingPlatforms.SPOTIFY
        assert results[0].external_id == "track123"
        assert results[0].isrc == "GBAYE7500101"

    @patch("backend.adapters.spotify_search_adapter.request_token")
    @patch("backend.adapters.spotify_search_adapter.httpx.AsyncClient")
    def test_search_non_200_returns_empty(self, mock_client_cls, mock_token, adapter):
        mock_token.return_value = {"access_token": "tok", "expires_in": 3600}

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await adapter.search("query")

        results = anyio.run(_run)
        assert results == []


class TestSpotifySearchAdapterGetMetadata:
    @pytest.fixture
    def adapter(self):
        return SpotifySearchAdapter({"client_id": "id", "client_secret": "secret"})

    @patch("backend.adapters.spotify_search_adapter.request_token")
    @patch("backend.adapters.spotify_search_adapter.httpx.AsyncClient")
    def test_get_metadata_success(self, mock_client_cls, mock_token, adapter):
        mock_token.return_value = {"access_token": "tok", "expires_in": 3600}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "abc",
            "name": "Song",
            "artists": [{"name": "Artist"}],
            "album": {"name": "Album", "images": []},
            "duration_ms": 200000,
            "explicit": True,
            "external_ids": {},
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await adapter.get_metadata("abc")

        result = anyio.run(_run)
        assert result is not None
        assert result.title == "Song"
        assert result.external_id == "abc"
        assert result.is_explicit is True

    @patch("backend.adapters.spotify_search_adapter.request_token")
    @patch("backend.adapters.spotify_search_adapter.httpx.AsyncClient")
    def test_get_metadata_not_found_returns_none(self, mock_client_cls, mock_token, adapter):
        mock_token.return_value = {"access_token": "tok", "expires_in": 3600}

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await adapter.get_metadata("nonexistent")

        result = anyio.run(_run)
        assert result is None


class TestSpotifySearchAdapterGetTrackUri:
    def test_returns_spotify_uri_format(self):
        adapter = SpotifySearchAdapter({"client_id": "id", "client_secret": "secret"})

        async def _run():
            return await adapter.get_track_uri("track123")

        result = anyio.run(_run)
        assert result == "spotify:track:track123"


class TestSpotifySearchAdapterTokenCaching:
    @patch("backend.adapters.spotify_search_adapter.request_token")
    @patch("backend.adapters.spotify_search_adapter.httpx.AsyncClient")
    def test_token_reused_on_second_call(self, mock_client_cls, mock_token):
        mock_token.return_value = {"access_token": "tok", "expires_in": 3600}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tracks": {"items": []}}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        adapter = SpotifySearchAdapter({"client_id": "id", "client_secret": "secret"})

        async def _run():
            await adapter.search("first")
            await adapter.search("second")

        anyio.run(_run)
        mock_token.assert_called_once()


class TestSpotifyAuthAdapter:
    @patch("backend.adapters.spotify_auth_adapter.request_token")
    def test_validate_credentials_success(self, mock_token):
        mock_token.return_value = {"access_token": "tok", "expires_in": 3600}

        async def _run():
            await SpotifyAuthAdapter.validate_credentials(
                {"client_id": "id", "client_secret": "secret"}
            )

        anyio.run(_run)
        mock_token.assert_called_once()

    @patch("backend.adapters.spotify_auth_adapter.request_token")
    def test_validate_credentials_failure_raises(self, mock_token):
        mock_token.side_effect = InvalidPlatformCredentialsException("Spotify")

        async def _run():
            await SpotifyAuthAdapter.validate_credentials(
                {"client_id": "bad", "client_secret": "creds"}
            )

        with pytest.raises(InvalidPlatformCredentialsException):
            anyio.run(_run)


class TestRequestToken:
    @patch("backend.adapters.spotify_utils.httpx.AsyncClient")
    def test_missing_keys_raises(self, mock_client_cls):
        from backend.adapters.spotify_utils import request_token

        async def _run():
            await request_token({"client_id": "only_id"})

        with pytest.raises(InvalidPlatformCredentialsException):
            anyio.run(_run)

    @patch("backend.adapters.spotify_utils.httpx.AsyncClient")
    def test_non_200_raises(self, mock_client_cls):
        from backend.adapters.spotify_utils import request_token

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            await request_token({"client_id": "id", "client_secret": "secret"})

        with pytest.raises(InvalidPlatformCredentialsException):
            anyio.run(_run)

    @patch("backend.adapters.spotify_utils.httpx.AsyncClient")
    def test_success_returns_token_dict(self, mock_client_cls):
        from backend.adapters.spotify_utils import request_token

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "tok", "expires_in": 3600}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        async def _run():
            return await request_token({"client_id": "id", "client_secret": "secret"})

        result = anyio.run(_run)
        assert result["access_token"] == "tok"
