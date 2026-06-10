"""Tests for PlaybackControlService."""

# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import httpx
import pytest

from backend.adapters.spotify_playback_adapter import SpotifyPlaybackState
from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    SpotifyUpstreamException,
)
from backend.db.models.enum import ItemStatus
from backend.db.models.session import Session as SessionModel
from backend.db.models.song import Song
from backend.repositories.session_repo import SessionRepository
from backend.repositories.song_repo import SongRepository
from backend.services.platform_connection_service import PlatformConnectionService
from backend.services.playback_control_service import PlaybackControlService
from backend.services.playback_service import PlaybackService
from backend.services.queue_service import QueueService
from backend.services.room_service import RoomService


class TestPlaybackControlServicePlay:
    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def mock_session_repo(self):
        return MagicMock(spec=SessionRepository)

    @pytest.fixture
    def mock_song_repo(self):
        return MagicMock(spec=SongRepository)

    @pytest.fixture
    def mock_platform_connection_service(self):
        mock = MagicMock(spec=PlatformConnectionService)
        mock.get_valid_access_token = AsyncMock(return_value="access_token")
        return mock

    @pytest.fixture
    def mock_playback_service(self):
        mock = MagicMock(spec=PlaybackService)
        mock.finish_song = AsyncMock(return_value="finished")
        return mock

    @pytest.fixture
    def mock_queue_service(self):
        return MagicMock(spec=QueueService)

    @pytest.fixture
    def service(
        self,
        mock_room_service,
        mock_session_repo,
        mock_song_repo,
        mock_platform_connection_service,
        mock_playback_service,
        mock_queue_service,
    ):
        return PlaybackControlService(
            room_service=mock_room_service,
            session_repo=mock_session_repo,
            song_repo=mock_song_repo,
            platform_connection_service=mock_platform_connection_service,
            playback_service=mock_playback_service,
            queue_service=mock_queue_service,
        )

    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_play_success(
        self,
        mock_adapter_cls,
        service,
        mock_room_service,
        mock_song_repo,
        mock_session_repo,
    ):
        room_id = uuid4()
        user_id = uuid4()
        song_id = uuid4()

        mock_song = MagicMock(spec=Song)
        mock_song.external_id = "spotify_track_id"
        mock_song_repo.get_by_id.return_value = mock_song

        mock_session = MagicMock(spec=SessionModel)
        mock_session.id = uuid4()
        mock_session.current_device_id = "old_device"
        mock_session_repo.get_by_room.return_value = mock_session

        mock_adapter = AsyncMock()
        mock_adapter.play = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            await service.play(room_id, user_id, song_id, device_id="dev1")

        anyio.run(_run)

        mock_room_service.assert_host.assert_called_once_with(room_id, user_id)
        mock_song_repo.get_by_id.assert_called_once_with(song_id)
        mock_adapter.play.assert_called_once_with(
            "spotify:track:spotify_track_id", "dev1"
        )
        mock_session_repo.update.assert_called_once()
        call_args = mock_session_repo.update.call_args
        assert call_args[0][0] == mock_session.id
        update_data = call_args[0][1]
        assert update_data["playback_status"] == ItemStatus.PLAYING
        assert update_data["current_song_id"] == "spotify_track_id"
        assert update_data["current_device_id"] == "dev1"
        assert "playback_started_at" in update_data
        assert update_data["playback_position_ms"] == 0

    def test_play_non_host_forbidden(self, service, mock_room_service):
        mock_room_service.assert_host.side_effect = ForbiddenException(
            "Only the room host can perform this action"
        )

        async def _run():
            await service.play(uuid4(), uuid4(), uuid4())

        with pytest.raises(ForbiddenException):
            anyio.run(_run)

    def test_play_song_not_found(self, service, mock_room_service, mock_song_repo):
        mock_room_service.assert_host.return_value = MagicMock()
        mock_song_repo.get_by_id.return_value = None

        async def _run():
            await service.play(uuid4(), uuid4(), uuid4())

        with pytest.raises(EntityNotFoundException):
            anyio.run(_run)

    @patch("backend.services.playback_control_service.manager")
    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_play_broadcasts_state_changed(
        self,
        mock_adapter_cls,
        mock_manager,
        service,
        mock_room_service,
        mock_song_repo,
        mock_session_repo,
    ):
        room_id = uuid4()
        user_id = uuid4()
        song_id = uuid4()

        mock_song = MagicMock(spec=Song)
        mock_song.external_id = "spotify_track_id"
        mock_song_repo.get_by_id.return_value = mock_song

        mock_session = MagicMock(spec=SessionModel)
        mock_session.id = uuid4()
        mock_session.current_device_id = "dev1"
        mock_session_repo.get_by_room.return_value = mock_session

        mock_adapter = AsyncMock()
        mock_adapter.play = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter

        mock_manager.broadcast = AsyncMock()

        async def _run():
            await service.play(room_id, user_id, song_id)

        anyio.run(_run)

        mock_manager.broadcast.assert_called_once_with(
            {
                "type": "playback_state_changed",
                "room_id": str(room_id),
                "status": "playing",
                "track_id": "spotify_track_id",
            },
            str(room_id),
        )

    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_play_spotify_404_raises_upstream_exception(
        self, mock_adapter_cls, service, mock_room_service, mock_song_repo
    ):
        mock_song = MagicMock(spec=Song)
        mock_song.external_id = "track_id"
        mock_song_repo.get_by_id.return_value = mock_song

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_adapter = AsyncMock()
        mock_adapter.play.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            await service.play(uuid4(), uuid4(), uuid4())

        with pytest.raises(SpotifyUpstreamException) as exc_info:
            anyio.run(_run)

        assert "No active Spotify device" in str(exc_info.value)


class TestPlaybackControlServicePause:
    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def mock_session_repo(self):
        return MagicMock(spec=SessionRepository)

    @pytest.fixture
    def mock_song_repo(self):
        return MagicMock(spec=SongRepository)

    @pytest.fixture
    def mock_platform_connection_service(self):
        mock = MagicMock(spec=PlatformConnectionService)
        mock.get_valid_access_token = AsyncMock(return_value="access_token")
        return mock

    @pytest.fixture
    def mock_playback_service(self):
        mock = MagicMock(spec=PlaybackService)
        mock.finish_song = AsyncMock(return_value="finished")
        return mock

    @pytest.fixture
    def mock_queue_service(self):
        return MagicMock(spec=QueueService)

    @pytest.fixture
    def service(
        self,
        mock_room_service,
        mock_session_repo,
        mock_song_repo,
        mock_platform_connection_service,
        mock_playback_service,
        mock_queue_service,
    ):
        return PlaybackControlService(
            room_service=mock_room_service,
            session_repo=mock_session_repo,
            song_repo=mock_song_repo,
            platform_connection_service=mock_platform_connection_service,
            playback_service=mock_playback_service,
            queue_service=mock_queue_service,
        )

    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_pause_success(
        self, mock_adapter_cls, service, mock_room_service, mock_session_repo
    ):
        from datetime import datetime, timezone

        room_id = uuid4()
        user_id = uuid4()

        mock_session = MagicMock(spec=SessionModel)
        mock_session.id = uuid4()
        mock_session.playback_started_at = datetime.now(timezone.utc)
        mock_session.playback_position_ms = 0
        mock_session_repo.get_by_room.return_value = mock_session

        mock_adapter = AsyncMock()
        mock_adapter.pause = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            await service.pause(room_id, user_id)

        anyio.run(_run)

        mock_room_service.assert_host.assert_called_once_with(room_id, user_id)
        mock_adapter.pause.assert_called_once()
        mock_session_repo.update.assert_called_once()
        call_args = mock_session_repo.update.call_args
        assert call_args[0][0] == mock_session.id
        update_data = call_args[0][1]
        assert update_data["playback_status"] == ItemStatus.PAUSED
        assert "playback_position_ms" in update_data

    def test_pause_non_host_forbidden(self, service, mock_room_service):
        mock_room_service.assert_host.side_effect = ForbiddenException(
            "Only the room host can perform this action"
        )

        async def _run():
            await service.pause(uuid4(), uuid4())

        with pytest.raises(ForbiddenException):
            anyio.run(_run)

    @patch("backend.services.playback_control_service.manager")
    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_pause_broadcasts_state_changed(
        self,
        mock_adapter_cls,
        mock_manager,
        service,
        mock_room_service,
        mock_session_repo,
    ):
        room_id = uuid4()
        user_id = uuid4()

        mock_session = MagicMock(spec=SessionModel)
        mock_session.id = uuid4()
        mock_session_repo.get_by_room.return_value = mock_session

        mock_adapter = AsyncMock()
        mock_adapter.pause = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter

        mock_manager.broadcast = AsyncMock()

        async def _run():
            await service.pause(room_id, user_id)

        anyio.run(_run)

        mock_manager.broadcast.assert_called_once_with(
            {
                "type": "playback_state_changed",
                "room_id": str(room_id),
                "status": "paused",
                "track_id": None,
            },
            str(room_id),
        )

    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_pause_spotify_error_raises_upstream_exception(
        self, mock_adapter_cls, service, mock_room_service
    ):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_adapter = AsyncMock()
        mock_adapter.pause.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=mock_response
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            await service.pause(uuid4(), uuid4())

        with pytest.raises(SpotifyUpstreamException) as exc_info:
            anyio.run(_run)

        assert "permissions" in str(exc_info.value)


class TestPlaybackControlServiceSkip:
    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def mock_session_repo(self):
        return MagicMock(spec=SessionRepository)

    @pytest.fixture
    def mock_song_repo(self):
        return MagicMock(spec=SongRepository)

    @pytest.fixture
    def mock_platform_connection_service(self):
        mock = MagicMock(spec=PlatformConnectionService)
        mock.get_valid_access_token = AsyncMock(return_value="access_token")
        return mock

    @pytest.fixture
    def mock_playback_service(self):
        mock = MagicMock(spec=PlaybackService)
        mock.finish_song = AsyncMock(return_value="finished")
        return mock

    @pytest.fixture
    def mock_queue_service(self):
        return MagicMock(spec=QueueService)

    @pytest.fixture
    def service(
        self,
        mock_room_service,
        mock_session_repo,
        mock_song_repo,
        mock_platform_connection_service,
        mock_playback_service,
        mock_queue_service,
    ):
        return PlaybackControlService(
            room_service=mock_room_service,
            session_repo=mock_session_repo,
            song_repo=mock_song_repo,
            platform_connection_service=mock_platform_connection_service,
            playback_service=mock_playback_service,
            queue_service=mock_queue_service,
        )

    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_skip_plays_next_queue_item(
        self,
        mock_adapter_cls,
        service,
        mock_room_service,
        mock_session_repo,
        mock_playback_service,
        mock_queue_service,
    ):
        room_id = uuid4()
        user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock(spec=SessionModel)
        mock_session.id = session_id
        mock_session_repo.get_by_room.return_value = mock_session

        mock_next_song = MagicMock(spec=Song)
        mock_next_song.external_id = "next_track_id"
        mock_next_item = MagicMock()
        mock_next_item.song = mock_next_song
        mock_queue_service.get_current_song.return_value = mock_next_item

        mock_adapter = AsyncMock()
        mock_adapter.play = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            await service.skip(room_id, user_id)

        anyio.run(_run)

        mock_room_service.assert_host.assert_called_once_with(room_id, user_id)
        mock_playback_service.finish_song.assert_called_once_with(session_id)
        mock_queue_service.get_current_song.assert_called_once_with(session_id)
        mock_adapter.play.assert_called_once_with("spotify:track:next_track_id")
        mock_session_repo.update.assert_called_once()
        call_args = mock_session_repo.update.call_args
        assert call_args[0][0] == session_id
        update_data = call_args[0][1]
        assert update_data["playback_status"] == ItemStatus.PLAYING
        assert update_data["current_song_id"] == "next_track_id"
        assert update_data["playback_position_ms"] == 0

    def test_skip_non_host_forbidden(self, service, mock_room_service):
        mock_room_service.assert_host.side_effect = ForbiddenException(
            "Only the room host can perform this action"
        )

        async def _run():
            await service.skip(uuid4(), uuid4())

        with pytest.raises(ForbiddenException):
            anyio.run(_run)

    @patch("backend.services.playback_control_service.manager")
    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_skip_pauses_when_queue_empty(
        self,
        mock_adapter_cls,
        mock_manager,
        service,
        mock_room_service,
        mock_session_repo,
        mock_playback_service,
        mock_queue_service,
    ):
        room_id = uuid4()
        user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock(spec=SessionModel)
        mock_session.id = session_id
        mock_session_repo.get_by_room.return_value = mock_session

        mock_queue_service.get_current_song.return_value = None

        mock_adapter = AsyncMock()
        mock_adapter.pause = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter

        mock_manager.broadcast = AsyncMock()

        async def _run():
            await service.skip(room_id, user_id)

        anyio.run(_run)

        mock_playback_service.finish_song.assert_called_once_with(session_id)
        mock_adapter.pause.assert_called_once()
        mock_session_repo.update.assert_called_once_with(
            session_id, {"playback_status": ItemStatus.STOPPED}
        )
        mock_manager.broadcast.assert_called_once_with(
            {
                "type": "playback_state_changed",
                "room_id": str(room_id),
                "status": "stopped",
                "track_id": None,
            },
            str(room_id),
        )

    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_skip_spotify_play_error_raises_upstream_exception(
        self,
        mock_adapter_cls,
        service,
        mock_room_service,
        mock_session_repo,
        mock_playback_service,
        mock_queue_service,
    ):
        room_id = uuid4()
        user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock(spec=SessionModel)
        mock_session.id = session_id
        mock_session_repo.get_by_room.return_value = mock_session

        mock_next_song = MagicMock(spec=Song)
        mock_next_song.external_id = "next_track_id"
        mock_next_item = MagicMock()
        mock_next_item.song = mock_next_song
        mock_queue_service.get_current_song.return_value = mock_next_item

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_adapter = AsyncMock()
        mock_adapter.play.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=mock_response
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            await service.skip(room_id, user_id)

        with pytest.raises(SpotifyUpstreamException) as exc_info:
            anyio.run(_run)

        assert "permissions" in str(exc_info.value)


class TestPlaybackControlServiceGetCurrentPlayback:
    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def mock_session_repo(self):
        return MagicMock(spec=SessionRepository)

    @pytest.fixture
    def mock_song_repo(self):
        return MagicMock(spec=SongRepository)

    @pytest.fixture
    def mock_platform_connection_service(self):
        mock = MagicMock(spec=PlatformConnectionService)
        mock.get_valid_access_token = AsyncMock(return_value="access_token")
        return mock

    @pytest.fixture
    def mock_playback_service(self):
        mock = MagicMock(spec=PlaybackService)
        mock.finish_song = AsyncMock(return_value="finished")
        return mock

    @pytest.fixture
    def mock_queue_service(self):
        return MagicMock(spec=QueueService)

    @pytest.fixture
    def service(
        self,
        mock_room_service,
        mock_session_repo,
        mock_song_repo,
        mock_platform_connection_service,
        mock_playback_service,
        mock_queue_service,
    ):
        return PlaybackControlService(
            room_service=mock_room_service,
            session_repo=mock_session_repo,
            song_repo=mock_song_repo,
            platform_connection_service=mock_platform_connection_service,
            playback_service=mock_playback_service,
            queue_service=mock_queue_service,
        )

    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_get_current_playback_returns_state(
        self, mock_adapter_cls, service, mock_room_service
    ):
        room_id = uuid4()
        user_id = uuid4()

        expected_state = SpotifyPlaybackState(
            is_playing=True,
            track_id="track123",
            progress_ms=45000,
            duration_ms=200000,
            device_id="dev1",
        )

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(return_value=expected_state)
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            return await service.get_current_playback(room_id, user_id)

        result = anyio.run(_run)

        mock_room_service.assert_host.assert_called_once_with(room_id, user_id)
        assert result == expected_state

    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_get_current_playback_returns_none(
        self, mock_adapter_cls, service, mock_room_service
    ):
        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(return_value=None)
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            return await service.get_current_playback(uuid4(), uuid4())

        result = anyio.run(_run)
        assert result is None

    @patch("backend.services.playback_control_service.SpotifyPlaybackAdapter")
    def test_get_current_playback_spotify_error_raises_upstream_exception(
        self, mock_adapter_cls, service, mock_room_service
    ):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            return await service.get_current_playback(uuid4(), uuid4())

        with pytest.raises(SpotifyUpstreamException) as exc_info:
            anyio.run(_run)

        assert "HTTP 500" in str(exc_info.value)
