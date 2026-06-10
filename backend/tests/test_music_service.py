"""Tests for MusicService."""

# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest

from backend.core.exceptions import EntityNotFoundException
from backend.db.models.enum import StreamingPlatforms
from backend.repositories.room_repo import RoomRepository
from backend.repositories.session_repo import SessionRepository
from backend.schemas.song_metadata import ReadSongMetadata
from backend.services.music_service import MusicService
from backend.services.platform_connection_service import PlatformConnectionService


class TestMusicServiceSearch:
    @pytest.fixture
    def mock_platform_service(self):
        return MagicMock(spec=PlatformConnectionService)

    @pytest.fixture
    def mock_room_repo(self):
        return MagicMock(spec=RoomRepository)

    @pytest.fixture
    def mock_session_repo(self):
        return MagicMock(spec=SessionRepository)

    @pytest.fixture
    def music_service(self, mock_platform_service, mock_room_repo, mock_session_repo):
        return MusicService(mock_platform_service, mock_room_repo, mock_session_repo)

    @patch("backend.services.music_service.AdapterFactory")
    def test_search_spotify_uses_host_app_credentials(
        self,
        mock_factory,
        music_service,
        mock_platform_service,
        mock_room_repo,
        mock_session_repo,
    ):
        room_id = uuid4()
        host_id = uuid4()

        mock_session = MagicMock()
        mock_session.current_platform = StreamingPlatforms.SPOTIFY
        mock_session_repo.get_by_room.return_value = mock_session

        mock_room = MagicMock()
        mock_room.host_user_id = host_id
        mock_room_repo.get_by_id.return_value = mock_room

        mock_platform_service.get_spotify_app_credentials.return_value = {
            "client_id": "host_client_id",
            "client_secret": "host_client_secret",
        }

        mock_adapter = AsyncMock()
        expected = [MagicMock(spec=ReadSongMetadata)]
        mock_adapter.search.return_value = expected
        mock_factory.create.return_value = mock_adapter

        async def _run():
            return await music_service.search(room_id, "query")

        result = anyio.run(_run)

        assert result == expected
        mock_session_repo.get_by_room.assert_called_once_with(room_id)
        mock_platform_service.get_spotify_app_credentials.assert_called_once_with(
            host_id
        )
        mock_factory.create.assert_called_once_with(
            StreamingPlatforms.SPOTIFY,
            {"client_id": "host_client_id", "client_secret": "host_client_secret"},
        )
        mock_adapter.search.assert_called_once_with("query")

    def test_search_spotify_raises_when_no_credentials(
        self,
        music_service,
        mock_platform_service,
        mock_room_repo,
        mock_session_repo,
    ):
        room_id = uuid4()
        host_id = uuid4()

        mock_session = MagicMock()
        mock_session.current_platform = StreamingPlatforms.SPOTIFY
        mock_session_repo.get_by_room.return_value = mock_session

        mock_room = MagicMock()
        mock_room.host_user_id = host_id
        mock_room_repo.get_by_id.return_value = mock_room

        mock_platform_service.get_spotify_app_credentials.return_value = None

        async def _run():
            return await music_service.search(room_id, "query")

        with pytest.raises(EntityNotFoundException):
            anyio.run(_run)

    @patch("backend.services.music_service.AdapterFactory")
    def test_search_non_spotify_uses_host_credentials(
        self,
        mock_factory,
        music_service,
        mock_platform_service,
        mock_room_repo,
        mock_session_repo,
    ):
        room_id = uuid4()
        host_id = uuid4()

        mock_session = MagicMock()
        mock_session.current_platform = StreamingPlatforms.TIDAL
        mock_session_repo.get_by_room.return_value = mock_session

        mock_room = MagicMock()
        mock_room.host_user_id = host_id
        mock_room_repo.get_by_id.return_value = mock_room

        mock_platform_service.get_decrypted_credentials.return_value = {
            "client_id": "id",
            "client_secret": "secret",
        }

        mock_adapter = AsyncMock()
        expected = [MagicMock(spec=ReadSongMetadata)]
        mock_adapter.search.return_value = expected
        mock_factory.create.return_value = mock_adapter

        async def _run():
            return await music_service.search(room_id, "query")

        result = anyio.run(_run)

        assert result == expected
        mock_session_repo.get_by_room.assert_called_once_with(room_id)
        mock_room_repo.get_by_id.assert_called_once_with(room_id)
        mock_platform_service.get_decrypted_credentials.assert_called_once_with(
            host_id, StreamingPlatforms.TIDAL
        )
        mock_factory.create.assert_called_once_with(
            StreamingPlatforms.TIDAL,
            {"client_id": "id", "client_secret": "secret"},
        )
        mock_adapter.search.assert_called_once_with("query")


class TestMusicServiceGetMetadata:
    @pytest.fixture
    def mock_platform_service(self):
        return MagicMock(spec=PlatformConnectionService)

    @pytest.fixture
    def mock_room_repo(self):
        return MagicMock(spec=RoomRepository)

    @pytest.fixture
    def mock_session_repo(self):
        return MagicMock(spec=SessionRepository)

    @pytest.fixture
    def music_service(self, mock_platform_service, mock_room_repo, mock_session_repo):
        return MusicService(mock_platform_service, mock_room_repo, mock_session_repo)

    @patch("backend.services.music_service.AdapterFactory")
    def test_get_metadata_delegates_to_adapter(
        self,
        mock_factory,
        music_service,
        mock_platform_service,
        mock_room_repo,
        mock_session_repo,
    ):
        room_id = uuid4()
        host_id = uuid4()

        mock_session = MagicMock()
        mock_session.current_platform = StreamingPlatforms.SPOTIFY
        mock_session_repo.get_by_room.return_value = mock_session

        mock_room = MagicMock()
        mock_room.host_user_id = host_id
        mock_room_repo.get_by_id.return_value = mock_room

        mock_platform_service.get_spotify_app_credentials.return_value = {
            "client_id": "host_id",
            "client_secret": "host_secret",
        }

        expected_metadata = MagicMock(spec=ReadSongMetadata)
        mock_adapter = AsyncMock()
        mock_adapter.get_metadata.return_value = expected_metadata
        mock_factory.create.return_value = mock_adapter

        async def _run():
            return await music_service.get_metadata(room_id, "track123")

        result = anyio.run(_run)

        assert result == expected_metadata
        mock_adapter.get_metadata.assert_called_once_with("track123")

    @patch("backend.services.music_service.AdapterFactory")
    def test_get_metadata_returns_none_when_not_found(
        self,
        mock_factory,
        music_service,
        mock_platform_service,
        mock_room_repo,
        mock_session_repo,
    ):
        room_id = uuid4()
        host_id = uuid4()

        mock_session = MagicMock()
        mock_session.current_platform = StreamingPlatforms.SPOTIFY
        mock_session_repo.get_by_room.return_value = mock_session

        mock_room = MagicMock()
        mock_room.host_user_id = host_id
        mock_room_repo.get_by_id.return_value = mock_room

        mock_platform_service.get_spotify_app_credentials.return_value = {
            "client_id": "host_id",
            "client_secret": "host_secret",
        }

        mock_adapter = AsyncMock()
        mock_adapter.get_metadata.return_value = None
        mock_factory.create.return_value = mock_adapter

        async def _run():
            return await music_service.get_metadata(room_id, "nonexistent")

        result = anyio.run(_run)
        assert result is None


class TestMusicServiceGetTrackUri:
    @pytest.fixture
    def mock_platform_service(self):
        return MagicMock(spec=PlatformConnectionService)

    @pytest.fixture
    def mock_room_repo(self):
        return MagicMock(spec=RoomRepository)

    @pytest.fixture
    def mock_session_repo(self):
        return MagicMock(spec=SessionRepository)

    @pytest.fixture
    def music_service(self, mock_platform_service, mock_room_repo, mock_session_repo):
        return MusicService(mock_platform_service, mock_room_repo, mock_session_repo)

    @patch("backend.services.music_service.AdapterFactory")
    def test_get_track_uri_delegates_to_adapter(
        self,
        mock_factory,
        music_service,
        mock_platform_service,
        mock_room_repo,
        mock_session_repo,
    ):
        room_id = uuid4()
        host_id = uuid4()

        mock_session = MagicMock()
        mock_session.current_platform = StreamingPlatforms.SPOTIFY
        mock_session_repo.get_by_room.return_value = mock_session

        mock_room = MagicMock()
        mock_room.host_user_id = host_id
        mock_room_repo.get_by_id.return_value = mock_room

        mock_platform_service.get_spotify_app_credentials.return_value = {
            "client_id": "host_id",
            "client_secret": "host_secret",
        }

        mock_adapter = AsyncMock()
        mock_adapter.get_track_uri.return_value = "spotify:track:abc"
        mock_factory.create.return_value = mock_adapter

        async def _run():
            return await music_service.get_track_uri(room_id, "abc")

        result = anyio.run(_run)

        assert result == "spotify:track:abc"
        mock_adapter.get_track_uri.assert_called_once_with("abc")
