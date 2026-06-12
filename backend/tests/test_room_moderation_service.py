"""Tests for RoomModerationService logic."""

# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest

from backend.core.exceptions import EntityNotFoundException, ForbiddenException
from backend.db.models.room_ban import RoomBan
from backend.db.models.user import User
from backend.repositories.room_ban_repo import RoomBanRepository
from backend.repositories.user_repo import UserRepository
from backend.services.room_moderation_service import RoomModerationService
from backend.services.room_service import RoomService


class TestRoomModerationService:
    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def mock_ban_repo(self):
        return MagicMock(spec=RoomBanRepository)

    @pytest.fixture
    def mock_user_repo(self):
        return MagicMock(spec=UserRepository)

    @pytest.fixture
    def service(self, mock_room_service, mock_ban_repo, mock_user_repo):
        return RoomModerationService(mock_room_service, mock_ban_repo, mock_user_repo)

    @pytest.fixture
    def room_id(self):
        return uuid4()

    @pytest.fixture
    def host_id(self):
        return uuid4()

    @pytest.fixture
    def target(self, room_id):
        member = MagicMock(spec=User)
        member.id = uuid4()
        member.username = "victim"
        member.room_id = room_id
        return member

    def test_kick_clears_room_broadcasts_and_disconnects(
        self, service, mock_room_service, mock_user_repo, room_id, host_id, target
    ):
        mock_user_repo.get_by_id.return_value = target

        def _run():
            with patch(
                "backend.services.room_moderation_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = AsyncMock()
                mock_manager.disconnect_user = AsyncMock()
                anyio.run(service.kick_user, room_id, host_id, target.id)
                return mock_manager

        manager = _run()
        mock_room_service.assert_host.assert_called_once_with(room_id, host_id)
        assert target.room_id is None
        mock_user_repo.save.assert_called_once_with(target)
        event = manager.broadcast.call_args[0][0]
        assert event["type"] == "member_kicked"
        assert event["payload"]["user_id"] == str(target.id)
        manager.disconnect_user.assert_awaited_once_with(target.id, str(room_id))

    def test_kick_not_in_room_raises(
        self, service, mock_user_repo, room_id, host_id, target
    ):
        target.room_id = uuid4()  # in a different room
        mock_user_repo.get_by_id.return_value = target

        with pytest.raises(EntityNotFoundException):
            anyio.run(service.kick_user, room_id, host_id, target.id)

    def test_kick_non_host_raises(
        self, service, mock_room_service, room_id, host_id, target
    ):
        mock_room_service.assert_host.side_effect = ForbiddenException()

        with pytest.raises(ForbiddenException):
            anyio.run(service.kick_user, room_id, host_id, target.id)

    def test_kick_self_raises(self, service, mock_user_repo, room_id, host_id):
        with pytest.raises(ForbiddenException):
            anyio.run(service.kick_user, room_id, host_id, host_id)
        mock_user_repo.get_by_id.assert_not_called()

    def test_ban_creates_record_and_broadcasts_banned(
        self, service, mock_ban_repo, mock_user_repo, room_id, host_id, target
    ):
        mock_user_repo.get_by_id.return_value = target

        def _run():
            with patch(
                "backend.services.room_moderation_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = AsyncMock()
                mock_manager.disconnect_user = AsyncMock()
                anyio.run(service.ban_user, room_id, host_id, target.id)
                return mock_manager

        manager = _run()
        mock_ban_repo.add.assert_called_once_with(room_id, target.id)
        assert target.room_id is None
        assert manager.broadcast.call_args[0][0]["type"] == "member_banned"

    def test_ban_absent_user_still_banned(
        self, service, mock_ban_repo, mock_user_repo, room_id, host_id, target
    ):
        target.room_id = None  # not currently in the room
        mock_user_repo.get_by_id.return_value = target

        def _run():
            with patch(
                "backend.services.room_moderation_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = AsyncMock()
                mock_manager.disconnect_user = AsyncMock()
                anyio.run(service.ban_user, room_id, host_id, target.id)
                return mock_manager

        manager = _run()
        mock_ban_repo.add.assert_called_once_with(room_id, target.id)
        manager.broadcast.assert_not_called()
        manager.disconnect_user.assert_awaited_once_with(target.id, str(room_id))

    def test_unban_removes_record(
        self, service, mock_room_service, mock_ban_repo, room_id, host_id, target
    ):
        service.unban_user(room_id, host_id, target.id)
        mock_room_service.assert_host.assert_called_once_with(room_id, host_id)
        mock_ban_repo.remove.assert_called_once_with(room_id, target.id)

    def test_list_bans_resolves_usernames(
        self, service, mock_ban_repo, mock_user_repo, room_id, host_id, target
    ):
        ban = MagicMock(spec=RoomBan)
        ban.user_id = target.id
        ban.created_at = __import__("datetime").datetime(2026, 6, 12, 12, 0, 0)
        mock_ban_repo.list_by_room.return_value = [ban]
        mock_user_repo.get_by_id.return_value = target

        result = service.list_bans(room_id, host_id)

        assert len(result) == 1
        assert result[0].user_id == target.id
        assert result[0].username == "victim"
