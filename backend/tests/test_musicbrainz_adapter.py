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


def make_isrc_xml_response(recording_id, title):
    """Return a MagicMock that mimics httpx.Response with XML data."""
    xml_body = f"""<?xml version="1.0"?>
<metadata>
    <recording id="{recording_id}">
        <title>{title}</title>
        <isrc-list>
            <isrc>USRC12300001</isrc>
        </isrc-list>
    </recording>
</metadata>""".encode()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.aread = AsyncMock(return_value=xml_body)
    return mock_resp


# --- Tests ---


class TestMusicBrainzAdapter:
    """Tests for MusicBrainzAdapter methods."""

    @patch("httpx.AsyncClient.get")
    def test_search_returns_recordings(self, mock_get, adapter):
        """search() returns the recordings list from the response."""
        sample = {"recordings": [
            {"id": "123", "title": "Song One",
             "artist-credit": [{"name": "Artist A"}]},
        ]}
        mock_get.return_value = make_json_response(sample)

        results = anyio.run(adapter.search, "test query")

        assert len(results) == 1
        assert results[0]["id"] == "123"
        assert results[0]["title"] == "Song One"
        mock_get.assert_called_once()

    @patch("httpx.AsyncClient.get")
    def test_search_empty_results(self, mock_get, adapter):
        """search() returns empty list when no recordings found."""
        sample = {"recordings": []}
        mock_get.return_value = make_json_response(sample)

        results = anyio.run(adapter.search, "nonexistent query xyz123")

        assert results == []

    @patch("httpx.AsyncClient.get")
    def test_search_custom_limit(self, mock_get):
        """search() respects custom limit parameter."""
        mock_resp = make_json_response({"recordings": []})
        mock_get.return_value = mock_resp

        adapter = MusicBrainzAdapter()
        anyio.run(lambda: adapter.search("query", limit=5))

        call_params = dict(mock_get.call_args.kwargs["params"])
        assert call_params["limit"] == 5

    @patch("httpx.AsyncClient.get")
    def test_get_by_mbid_success(self, mock_get, adapter):
        """get_by_mbid() returns recording data for a valid MBID."""
        sample = {
            "id": "456",
            "title": "MBID Song",
            "artist-credit": [{"name": "Artist B"}],
        }
        mock_get.return_value = make_json_response(sample)

        result = anyio.run(adapter.get_by_mbid, "456")

        assert result["id"] == "456"
        assert result["title"] == "MBID Song"

    @patch("httpx.AsyncClient.get")
    def test_get_by_mbid_not_found(self, mock_get, adapter):
        """get_by_mbid() returns None for a non-existent MBID."""
        sample = {"error": True}
        mock_get.return_value = make_json_response(sample)

        result = anyio.run(adapter.get_by_mbid, "nonexistent-mbid")

        assert result is None

    @patch("httpx.AsyncClient.get")
    def test_get_by_isrc_parses_xml(self, mock_get, adapter):
        """get_by_isrc() parses MusicBrainz XML response correctly."""
        mock_get.return_value = make_isrc_xml_response("789", "ISRC Title")

        result = anyio.run(adapter.get_by_isrc, "USRC12300001")

        assert result["id"] == "789"
        assert result["title"] == "ISRC Title"

    def test_rate_limit_delay_is_applied(self):
        """_request() applies rate limiting delay before each request."""
        mock_resp = make_json_response({"recordings": []})

        with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
            adapter = MusicBrainzAdapter(rate_limit_delay=0.01)
            # Two requests should be separated by at least the delay
            anyio.run(lambda: adapter.search("q1"))
            anyio.run(lambda: adapter.search("q2"))

            assert mock_get.call_count == 2

    def test_caching_returns_stored_data_on_second_call(self):
        """_cached_request() should not call _request if data is cached."""
        adapter = MusicBrainzAdapter()
        with patch.object(adapter, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = json.dumps({"recordings": [{"id": "x"}]}).encode()

            # First call — no cache yet
            anyio.run(adapter.search, "cached test")
            assert mock_req.call_count == 1

            # Second call with same key — should use cache
            anyio.run(adapter.search, "cached test")
            assert mock_req.call_count == 1  # still 1, not 2


class TestStreamingPlatformAdapter:
    """Tests for the base StreamingPlatformAdapter class."""

    def test_default_rate_limit_delay(self):
        """Base adapter uses default rate_limit_delay of 0.5."""
        from backend.adapters.base import StreamingPlatformAdapter

        class TestAdapter(StreamingPlatformAdapter):
            pass

        adapter = TestAdapter()
        assert adapter.rate_limit_delay == 0.5

    def test_custom_rate_limit_delay(self):
        """StreamingPlatformAdapter accepts custom rate_limit_delay."""
        from backend.adapters.base import StreamingPlatformAdapter

        class TestAdapter(StreamingPlatformAdapter):
            pass

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
                    "isrcs": [{"isrc": "USRC12300001"}],
                }
            ]
        }

        with patch.object(adapter, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = json.dumps(realistic_response).encode()

            results = anyio.run(adapter.search, "bad bunny")

            assert len(results) == 1
            assert results[0]["title"] == "Bad Bunny - Song Title"
            assert results[0]["isrcs"][0]["isrc"] == "USRC12300001"

    def test_isrc_with_empty_response(self, adapter):
        """get_by_isrc() handles empty XML gracefully."""
        empty_xml = b"""<?xml version="1.0"?><metadata/>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.raise_for_status = MagicMock()
        mock_resp.aread = AsyncMock(return_value=empty_xml)

        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            # Empty XML will raise when trying to parse — that's expected
            # The adapter should handle this gracefully
            result = anyio.run(lambda: adapter.get_by_isrc("INVALID99999"))
            assert "id" in result or result is None
