"""Tests for search router endpoints."""

# ruff: noqa: D101, D102
from unittest.mock import MagicMock
from uuid import uuid4

import anyio
import pytest

from backend.core.exceptions import EntityNotFoundException
from backend.db.models.enum import StreamingPlatforms
from backend.schemas.song_metadata import ReadSongMetadata
from backend.services.music_service import MusicService
from backend.services.song_service import SongService
from backend.api.search.router import search_tracks, get_track_metadata, _persist_song
from backend.schemas.song import CreateSong

from fastapi import HTTPException


class TestSearchTracks:
    @pytest.fixture
    def mock_music_service(self):
        mock = MagicMock(spec=MusicService)
        return mock

    @pytest.fixture
    def mock_song_service(self):
        return MagicMock(spec=SongService)

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = uuid4()
        return user

    def test_search_returns_results(self, mock_music_service, mock_song_service, mock_user):
        room_id = uuid4()
        results = [
            ReadSongMetadata(
                title="Song 1",
                artist="Artist 1",
                duration_ms=240000,
                external_id="track1",
                platform=StreamingPlatforms.SPOTIFY,
            ),
        ]

        async def mock_search(*args):
            return results

        mock_music_service.search = mock_search

        async def _run():
            return await search_tracks(
                room_id=room_id,
                q="test query",
                current_user=mock_user,
                music_service=mock_music_service,
                song_service=mock_song_service,
            )

        result = anyio.run(_run)

        assert result == results
        mock_song_service.get_or_create_song.assert_called_once()

    def test_search_raises_404_when_room_not_found(
        self, mock_music_service, mock_song_service, mock_user
    ):
        room_id = uuid4()

        async def mock_search(*args):
            raise EntityNotFoundException("Room", room_id)

        mock_music_service.search = mock_search

        async def _run():
            return await search_tracks(
                room_id=room_id,
                q="test",
                current_user=mock_user,
                music_service=mock_music_service,
                song_service=mock_song_service,
            )

        with pytest.raises(HTTPException) as exc_info:
            anyio.run(_run)

        assert exc_info.value.status_code == 404

    def test_search_persists_each_result(
        self, mock_music_service, mock_song_service, mock_user
    ):
        room_id = uuid4()
        results = [
            ReadSongMetadata(
                title="Song 1",
                artist="Artist 1",
                duration_ms=180000,
                external_id="t1",
                platform=StreamingPlatforms.SPOTIFY,
            ),
            ReadSongMetadata(
                title="Song 2",
                artist="Artist 2",
                duration_ms=200000,
                external_id="t2",
                platform=StreamingPlatforms.SPOTIFY,
            ),
        ]

        async def mock_search(*args):
            return results

        mock_music_service.search = mock_search

        async def _run():
            return await search_tracks(
                room_id=room_id,
                q="query",
                current_user=mock_user,
                music_service=mock_music_service,
                song_service=mock_song_service,
            )

        anyio.run(_run)

        assert mock_song_service.get_or_create_song.call_count == 2

    def test_search_skips_persist_when_external_id_none(
        self, mock_music_service, mock_song_service, mock_user
    ):
        room_id = uuid4()
        results = [
            ReadSongMetadata(
                title="Song 1",
                artist="Artist 1",
                duration_ms=180000,
                external_id=None,
                platform=StreamingPlatforms.SPOTIFY,
            ),
        ]

        async def mock_search(*args):
            return results

        mock_music_service.search = mock_search

        async def _run():
            return await search_tracks(
                room_id=room_id,
                q="query",
                current_user=mock_user,
                music_service=mock_music_service,
                song_service=mock_song_service,
            )

        anyio.run(_run)

        mock_song_service.get_or_create_song.assert_not_called()


class TestGetTrackMetadata:
    @pytest.fixture
    def mock_music_service(self):
        return MagicMock(spec=MusicService)

    @pytest.fixture
    def mock_song_service(self):
        return MagicMock(spec=SongService)

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = uuid4()
        return user

    def test_get_metadata_returns_track(
        self, mock_music_service, mock_song_service, mock_user
    ):
        room_id = uuid4()
        metadata = ReadSongMetadata(
            title="Track",
            artist="Artist",
            duration_ms=300000,
            external_id="ext123",
            platform=StreamingPlatforms.SPOTIFY,
        )

        async def mock_get_metadata(*args):
            return metadata

        mock_music_service.get_metadata = mock_get_metadata

        async def _run():
            return await get_track_metadata(
                external_id="ext123",
                room_id=room_id,
                current_user=mock_user,
                music_service=mock_music_service,
                song_service=mock_song_service,
            )

        result = anyio.run(_run)

        assert result == metadata
        mock_song_service.get_or_create_song.assert_called_once()

    def test_get_metadata_raises_404_when_room_not_found(
        self, mock_music_service, mock_song_service, mock_user
    ):
        room_id = uuid4()

        async def mock_get_metadata(*args):
            raise EntityNotFoundException("Room", room_id)

        mock_music_service.get_metadata = mock_get_metadata

        async def _run():
            return await get_track_metadata(
                external_id="ext123",
                room_id=room_id,
                current_user=mock_user,
                music_service=mock_music_service,
                song_service=mock_song_service,
            )

        with pytest.raises(HTTPException) as exc_info:
            anyio.run(_run)

        assert exc_info.value.status_code == 404

    def test_get_metadata_raises_404_when_track_not_found(
        self, mock_music_service, mock_song_service, mock_user
    ):
        room_id = uuid4()

        async def mock_get_metadata(*args):
            return None

        mock_music_service.get_metadata = mock_get_metadata

        async def _run():
            return await get_track_metadata(
                external_id="nonexistent",
                room_id=room_id,
                current_user=mock_user,
                music_service=mock_music_service,
                song_service=mock_song_service,
            )

        with pytest.raises(HTTPException) as exc_info:
            anyio.run(_run)

        assert exc_info.value.status_code == 404
        assert "nonexistent" in exc_info.value.detail

    def test_get_metadata_persists_result(
        self, mock_music_service, mock_song_service, mock_user
    ):
        room_id = uuid4()
        metadata = ReadSongMetadata(
            title="Track",
            artist="Artist",
            duration_ms=250000,
            external_id="ext456",
            platform=StreamingPlatforms.SPOTIFY,
        )

        async def mock_get_metadata(*args):
            return metadata

        mock_music_service.get_metadata = mock_get_metadata

        async def _run():
            return await get_track_metadata(
                external_id="ext456",
                room_id=room_id,
                current_user=mock_user,
                music_service=mock_music_service,
                song_service=mock_song_service,
            )

        anyio.run(_run)

        call_args = mock_song_service.get_or_create_song.call_args[0][0]
        assert call_args.external_id == "ext456"
        assert call_args.duration == 250.0


class TestPersistSong:
    @pytest.fixture
    def mock_song_service(self):
        return MagicMock(spec=SongService)

    def test_persist_skips_when_external_id_none(self, mock_song_service):
        metadata = ReadSongMetadata(
            title="Song",
            artist="Artist",
            external_id=None,
            platform=StreamingPlatforms.SPOTIFY,
        )

        _persist_song(metadata, mock_song_service)

        mock_song_service.get_or_create_song.assert_not_called()

    def test_persist_skips_when_platform_none(self, mock_song_service):
        metadata = ReadSongMetadata(
            title="Song",
            artist="Artist",
            external_id="abc",
            platform=None,
        )

        _persist_song(metadata, mock_song_service)

        mock_song_service.get_or_create_song.assert_not_called()

    def test_persist_converts_duration_ms_to_seconds(self, mock_song_service):
        metadata = ReadSongMetadata(
            title="Song",
            artist="Artist",
            external_id="abc",
            platform=StreamingPlatforms.SPOTIFY,
            duration_ms=180000,
        )

        _persist_song(metadata, mock_song_service)

        call_args = mock_song_service.get_or_create_song.call_args[0][0]
        assert call_args.duration == 180.0

    def test_persist_uses_zero_when_duration_ms_none(self, mock_song_service):
        metadata = ReadSongMetadata(
            title="Song",
            artist="Artist",
            external_id="abc",
            platform=StreamingPlatforms.SPOTIFY,
            duration_ms=None,
        )

        _persist_song(metadata, mock_song_service)

        call_args = mock_song_service.get_or_create_song.call_args[0][0]
        assert call_args.duration == 0.0
