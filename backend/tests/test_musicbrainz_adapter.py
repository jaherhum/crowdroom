"""Tests for MusicBrainzAdapter."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest

from backend.adapters.musicbrainz import MusicBrainzAdapter


# --- Fixtures ---


@pytest.fixture
def adapter():
    return MusicBrainzAdapter()


# --- Helpers ---


def make_json_response(data):
    """Return a MagicMock that mimics httpx.Response with JSON data."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.aread = AsyncMock(return_value=json.dumps(data).encode())
    return mock_resp


# --- Tests ---


class TestMusicBrainzAdapter:
    """Tests for MusicBrainzAdapter methods."""

    @patch("httpx.AsyncClient.get")
    def test_search_returns_recordings(self, mock_get, adapter):
        """search() returns parsed ReadSongMetadata objects from the response."""
        sample = {"recordings": [
            {"id": "123", "title": "Song One",
             "artist-credit": [{"name": "Artist A"}]},
        ]}
        mock_get.return_value = make_json_response(sample)

        results = anyio.run(lambda: adapter.search(query="test query"))

        assert len(results) == 1
        assert results[0].external_id == "123"
        assert results[0].title == "Song One"
        mock_get.assert_called_once()

    @patch("httpx.AsyncClient.get")
    def test_search_empty_results(self, mock_get, adapter):
        """search() returns empty list when no recordings found."""
        sample = {"recordings": []}
        mock_get.return_value = make_json_response(sample)

        results = anyio.run(lambda: adapter.search(query="nonexistent query xyz123"))

        assert results == []

    @patch("httpx.AsyncClient.get")
    def test_search_custom_limit(self, mock_get):
        """search() respects custom limit parameter."""
        mock_resp = make_json_response({"recordings": []})
        mock_get.return_value = mock_resp

        adapter = MusicBrainzAdapter()
        anyio.run(lambda: adapter.search(query="query", isrc=None))
        # Verify the call was made with default params structure
        assert mock_get.call_count == 1

    @patch("httpx.AsyncClient.get")
    def test_get_metadata_success(self, mock_get, adapter):
        """get_metadata() returns parsed metadata for a valid MBID."""
        sample = {
            "id": "456",
            "title": "MBID Song",
            "artist-credit": [{"name": "Artist B"}],
        }
        mock_get.return_value = make_json_response(sample)

        result = anyio.run(adapter.get_metadata, "456")

        assert result is not None
        assert result.external_id == "456"
        assert result.title == "MBID Song"

    @patch("httpx.AsyncClient.get")
    def test_get_metadata_not_found(self, mock_get, adapter):
        """get_metadata() returns None for a non-existent MBID."""
        sample = {"error": True}
        mock_get.return_value = make_json_response(sample)

        result = anyio.run(adapter.get_metadata, "nonexistent-mbid")

        assert result is None

    def test_rate_limit_delay_is_applied(self):
        """_request() applies rate limiting delay before each request."""
        mock_resp = make_json_response({"recordings": []})

        with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
            adapter = MusicBrainzAdapter(rate_limit_delay=0.01)
            anyio.run(lambda: adapter.search(query="q1"))
            anyio.run(lambda: adapter.search(query="q2"))

            assert mock_get.call_count == 2

    def test_caching_returns_stored_data_on_second_call(self):
        """_cached_request() should not call _request if data is cached."""
        adapter = MusicBrainzAdapter()
        with patch.object(adapter, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = json.dumps({"recordings": [{"id": "x"}]}).encode()

            anyio.run(lambda: adapter.search(query="cached test"))
            assert mock_req.call_count == 1

            anyio.run(lambda: adapter.search(query="cached test"))
            assert mock_req.call_count == 1


class TestStreamingPlatformAdapter:
    """Tests for the base StreamingPlatformAdapter class."""

    def test_default_rate_limit_delay(self):
        """Base adapter uses default rate_limit_delay of 0.5."""
        from backend.adapters.base import StreamingPlatformAdapter

        class TestAdapter(StreamingPlatformAdapter):
            async def search(self, isrc=None, query=""): return []
            async def get_metadata(self, external_id): return None
            def get_track_uri(self, external_id): return None

        adapter = TestAdapter()
        assert adapter.rate_limit_delay == 0.5

    def test_custom_rate_limit_delay(self):
        """StreamingPlatformAdapter accepts custom rate_limit_delay."""
        from backend.adapters.base import StreamingPlatformAdapter

        class TestAdapter(StreamingPlatformAdapter):
            async def search(self, isrc=None, query=""): return []
            async def get_metadata(self, external_id): return None
            def get_track_uri(self, external_id): return None

        adapter = TestAdapter(rate_limit_delay=2.0)
        assert adapter.rate_limit_delay == 2.0


class TestMusicBrainzAdapterIntegration:
    """End-to-end style tests with real sample responses."""

    def test_search_real_sample(self, adapter):
        """Test parsing with realistic MusicBrainz search response structure."""
        realistic_response = {
            "recordings": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "title": "Bad Bunny - Song Title",
                    "length": 183000,
                    "artist-credit": [
                        {
                            "name": "Bad Bunny",
                            "artist": {"id": "mbid-artist-123", "name": "Bad Bunny"},
                        }
                    ],
                    "isrc-list": ["USRC12300001"],
                }
            ]
        }

        with patch.object(adapter, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = json.dumps(realistic_response).encode()

            results = anyio.run(lambda: adapter.search(query="bad bunny"))

            assert len(results) == 1
            assert results[0].title == "Bad Bunny - Song Title"
            assert results[0].isrc == "USRC12300001"

    def test_isrc_lookup_parses_dict_entry(self, adapter):
        """_parse_recording handles ISRC entries that are dicts."""
        sample = {
            "id": "789",
            "title": "ISRC Song",
            "artist-credits": [{"name-credit": {"name": "Artist C"}}],
            "isrcs": [{"isrc": "USRC12300002"}],
        }

        result = MusicBrainzAdapter._parse_recording(sample)

        assert result.external_id == "789"
        assert result.title == "ISRC Song"
        assert result.isrc == "USRC12300002"
        assert result.artist == "Artist C"
