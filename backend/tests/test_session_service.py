"""Tests for SessionService logic."""

# ruff: noqa: D101, D102
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.core.exceptions import EntityNotFoundException
from backend.db.models.enum import ItemStatus, StreamingPlatforms
from backend.db.models.session import Session as SessionModel
from backend.repositories.session_repo import SessionRepository
from backend.schemas.session import CreateSession, UpdateSession
from backend.services.session_service import SessionService


class TestSessionService:
    @pytest.fixture
    def mock_session_repo(self):
        return MagicMock(spec=SessionRepository)

    @pytest.fixture
    def session_service(self, mock_session_repo):
        return SessionService(mock_session_repo)

    def test_get_session_success(self, session_service, mock_session_repo):
        session_id = uuid4()
        expected = MagicMock(spec=SessionModel)
        mock_session_repo.get_by_id.return_value = expected

        result = session_service.get_session(session_id)

        assert result == expected
        mock_session_repo.get_by_id.assert_called_once_with(session_id)

    def test_get_session_not_found(self, session_service, mock_session_repo):
        session_id = uuid4()
        mock_session_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            session_service.get_session(session_id)

    def test_get_all_sessions(self, session_service, mock_session_repo):
        sessions = [MagicMock(spec=SessionModel), MagicMock(spec=SessionModel)]
        mock_session_repo.get_all.return_value = sessions

        result = session_service.get_all_sessions()

        assert result == sessions
        mock_session_repo.get_all.assert_called_once()

    def test_create_session(self, session_service, mock_session_repo):
        room_id = uuid4()
        data = CreateSession(
            room_id=room_id, current_platform=StreamingPlatforms.SPOTIFY
        )
        mock_session_repo.create.return_value = MagicMock(spec=SessionModel)

        result = session_service.create_session(data)

        assert result is not None
        mock_session_repo.create.assert_called_once()
        created = mock_session_repo.create.call_args[0][0]
        assert created.room_id == room_id
        assert created.current_platform == StreamingPlatforms.SPOTIFY

    def test_update_session_success(self, session_service, mock_session_repo):
        session_id = uuid4()
        existing = MagicMock(spec=SessionModel)
        mock_session_repo.get_by_id.return_value = existing
        mock_session_repo.update.return_value = existing

        data = UpdateSession(current_song_id="track_123")
        result = session_service.update_session(session_id, data)

        assert result == existing
        mock_session_repo.update.assert_called_once_with(
            session_id, {"current_song_id": "track_123"}
        )

    def test_update_session_not_found(self, session_service, mock_session_repo):
        session_id = uuid4()
        mock_session_repo.get_by_id.return_value = None

        data = UpdateSession(current_song_id="track_123")
        with pytest.raises(EntityNotFoundException):
            session_service.update_session(session_id, data)

    def test_update_session_playback_fields(self, session_service, mock_session_repo):
        session_id = uuid4()
        existing = MagicMock(spec=SessionModel)
        mock_session_repo.get_by_id.return_value = existing
        mock_session_repo.update.return_value = existing

        now = datetime.now()
        data = UpdateSession(
            playback_status=ItemStatus.PLAYING,
            playback_position_ms=42000,
            playback_started_at=now,
            current_device_id="device_abc",
        )
        result = session_service.update_session(session_id, data)

        assert result == existing
        mock_session_repo.update.assert_called_once_with(
            session_id,
            {
                "playback_status": ItemStatus.PLAYING,
                "playback_position_ms": 42000,
                "playback_started_at": now,
                "current_device_id": "device_abc",
            },
        )

    def test_delete_session_success(self, session_service, mock_session_repo):
        session_id = uuid4()
        mock_session_repo.get_by_id.return_value = MagicMock(spec=SessionModel)

        session_service.delete_session(session_id)

        mock_session_repo.delete.assert_called_once_with(session_id)

    def test_delete_session_not_found(self, session_service, mock_session_repo):
        session_id = uuid4()
        mock_session_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            session_service.delete_session(session_id)


class TestSessionSchemas:
    def test_update_session_exclude_unset(self):
        data = UpdateSession(playback_status=ItemStatus.PAUSED)
        dumped = data.model_dump(exclude_unset=True)

        assert dumped == {"playback_status": ItemStatus.PAUSED}
        assert "current_song_id" not in dumped
        assert "playback_position_ms" not in dumped

    def test_update_session_all_playback_fields(self):
        now = datetime.now()
        data = UpdateSession(
            playback_status=ItemStatus.PLAYING,
            playback_position_ms=15000,
            playback_started_at=now,
            current_device_id="dev_1",
        )
        dumped = data.model_dump(exclude_unset=True)

        assert dumped == {
            "playback_status": ItemStatus.PLAYING,
            "playback_position_ms": 15000,
            "playback_started_at": now,
            "current_device_id": "dev_1",
        }

    def test_read_session_from_model(self):
        from backend.schemas.session import ReadSession

        session_id = uuid4()
        room_id = uuid4()
        now = datetime.now()

        model = SessionModel(
            id=session_id,
            room_id=room_id,
            current_platform=StreamingPlatforms.SPOTIFY,
            current_song_id="track_xyz",
            last_updated=now,
            playback_status=ItemStatus.PLAYING,
            playback_position_ms=30000,
            playback_started_at=now,
            current_device_id="device_123",
        )

        schema = ReadSession.model_validate(model)

        assert schema.id == session_id
        assert schema.playback_status == ItemStatus.PLAYING
        assert schema.playback_position_ms == 30000
        assert schema.playback_started_at == now
        assert schema.current_device_id == "device_123"

    def test_read_session_nullable_playback_fields(self):
        from backend.schemas.session import ReadSession

        session_id = uuid4()
        room_id = uuid4()
        now = datetime.now()

        model = SessionModel(
            id=session_id,
            room_id=room_id,
            current_platform=StreamingPlatforms.SPOTIFY,
            current_song_id=None,
            last_updated=now,
            playback_status=None,
            playback_position_ms=None,
            playback_started_at=None,
            current_device_id=None,
        )

        schema = ReadSession.model_validate(model)

        assert schema.playback_status is None
        assert schema.playback_position_ms is None
        assert schema.playback_started_at is None
        assert schema.current_device_id is None
