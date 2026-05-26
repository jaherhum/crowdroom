"""Tests for RoomMembershipService logic."""

# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest

from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    UserAlreadyInRoomException,
)
from backend.db.models.room import Room
from backend.db.models.user import User
from backend.repositories.room_repo import RoomRepository
from backend.repositories.user_repo import UserRepository
from backend.services.room_invite_service import RoomInviteService
from backend.services.room_membership_service import RoomMembershipService
from backend.services.room_service import RoomService


class TestJoinRoom:
    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def mock_invite_service(self):
        return MagicMock(spec=RoomInviteService)

    @pytest.fixture
    def mock_user_repo(self):
        return MagicMock(spec=UserRepository)

    @pytest.fixture
    def mock_room_repo(self):
        return MagicMock(spec=RoomRepository)

    @pytest.fixture
    def membership_service(
        self,
        mock_room_service,
        mock_invite_service,
        mock_user_repo,
        mock_room_repo,
    ):
        return RoomMembershipService(
            mock_room_service,
            mock_invite_service,
            mock_user_repo,
            mock_room_repo,
        )

    @pytest.fixture
    def user(self):
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.username = "testuser"
        mock_user.room_id = None
        return mock_user

    @pytest.fixture
    def public_room(self):
        mock_room = MagicMock(spec=Room)
        mock_room.id = uuid4()
        mock_room.host_user_id = uuid4()
        mock_room.room_name = "Public Room"
        mock_room.is_private = False
        return mock_room

    @pytest.fixture
    def private_room(self):
        mock_room = MagicMock(spec=Room)
        mock_room.id = uuid4()
        mock_room.host_user_id = uuid4()
        mock_room.room_name = "Private Room"
        mock_room.is_private = True
        return mock_room

    def test_join_public_room_success(
        self,
        membership_service,
        mock_room_service,
        mock_user_repo,
        user,
        public_room,
    ):
        mock_room_service.get_room.return_value = public_room
        mock_broadcast = AsyncMock()

        async def _run():
            with patch(
                "backend.services.room_membership_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await membership_service.join_room(public_room.id, user)

        anyio.run(_run)

        assert user.room_id == public_room.id
        mock_user_repo.save.assert_called_once_with(user)
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert call_args[0][0]["type"] == "member_joined"
        assert call_args[0][0]["payload"]["user_id"] == str(user.id)

    def test_join_private_room_with_valid_pin(
        self,
        membership_service,
        mock_room_service,
        mock_invite_service,
        mock_user_repo,
        user,
        private_room,
    ):
        mock_room_service.get_room.return_value = private_room
        mock_invite_service.validate_and_consume_invite.return_value = False
        mock_room_service.verify_pin.return_value = True
        mock_broadcast = AsyncMock()

        async def _run():
            with patch(
                "backend.services.room_membership_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await membership_service.join_room(
                    private_room.id, user, "1234", None
                )

        anyio.run(_run)

        assert user.room_id == private_room.id
        mock_user_repo.save.assert_called_once_with(user)

    def test_join_private_room_with_valid_invite(
        self,
        membership_service,
        mock_room_service,
        mock_invite_service,
        mock_user_repo,
        user,
        private_room,
    ):
        mock_room_service.get_room.return_value = private_room
        mock_invite_service.validate_and_consume_invite.return_value = True
        mock_broadcast = AsyncMock()

        async def _run():
            with patch(
                "backend.services.room_membership_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await membership_service.join_room(
                    private_room.id, user, None, "abc123token"
                )

        anyio.run(_run)

        assert user.room_id == private_room.id
        mock_invite_service.validate_and_consume_invite.assert_called_once_with(
            "abc123token", private_room.id
        )

    def test_join_private_room_no_credentials_forbidden(
        self,
        membership_service,
        mock_room_service,
        mock_invite_service,
        user,
        private_room,
    ):
        mock_room_service.get_room.return_value = private_room
        mock_invite_service.validate_and_consume_invite.return_value = False

        async def _run():
            with patch(
                "backend.services.room_membership_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = AsyncMock()
                await membership_service.join_room(
                    private_room.id, user
                )

        with pytest.raises(ForbiddenException):
            anyio.run(_run)

    def test_join_private_room_wrong_pin_forbidden(
        self,
        membership_service,
        mock_room_service,
        mock_invite_service,
        user,
        private_room,
    ):
        mock_room_service.get_room.return_value = private_room
        mock_invite_service.validate_and_consume_invite.return_value = False
        mock_room_service.verify_pin.return_value = False

        async def _run():
            with patch(
                "backend.services.room_membership_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = AsyncMock()
                await membership_service.join_room(
                    private_room.id, user, "0000", None
                )

        with pytest.raises(ForbiddenException):
            anyio.run(_run)

    def test_join_user_already_in_different_room_conflict(
        self, membership_service, user, public_room
    ):
        user.room_id = uuid4()

        async def _run():
            await membership_service.join_room(public_room.id, user)

        with pytest.raises(UserAlreadyInRoomException):
            anyio.run(_run)

    def test_join_same_room_idempotent(
        self,
        membership_service,
        mock_room_service,
        mock_user_repo,
        user,
        public_room,
    ):
        user.room_id = public_room.id

        async def _run():
            with patch(
                "backend.services.room_membership_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = AsyncMock()
                await membership_service.join_room(public_room.id, user)

        anyio.run(_run)

        mock_room_service.get_room.assert_not_called()
        mock_user_repo.save.assert_not_called()

    def test_join_room_not_found(
        self, membership_service, mock_room_service, user
    ):
        room_id = uuid4()
        mock_room_service.get_room.side_effect = EntityNotFoundException(
            "Room", room_id
        )

        async def _run():
            await membership_service.join_room(room_id, user)

        with pytest.raises(EntityNotFoundException):
            anyio.run(_run)


class TestLeaveRoom:
    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def mock_invite_service(self):
        return MagicMock(spec=RoomInviteService)

    @pytest.fixture
    def mock_user_repo(self):
        return MagicMock(spec=UserRepository)

    @pytest.fixture
    def mock_room_repo(self):
        return MagicMock(spec=RoomRepository)

    @pytest.fixture
    def membership_service(
        self,
        mock_room_service,
        mock_invite_service,
        mock_user_repo,
        mock_room_repo,
    ):
        return RoomMembershipService(
            mock_room_service,
            mock_invite_service,
            mock_user_repo,
            mock_room_repo,
        )

    @pytest.fixture
    def room(self):
        mock_room = MagicMock(spec=Room)
        mock_room.id = uuid4()
        mock_room.host_user_id = uuid4()
        mock_room.room_name = "Test Room"
        mock_room.users = []
        return mock_room

    @pytest.fixture
    def user(self, room):
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.username = "testuser"
        mock_user.room_id = room.id
        return mock_user

    def test_leave_room_success(
        self,
        membership_service,
        mock_room_service,
        mock_user_repo,
        user,
        room,
    ):
        mock_room_service.get_room.return_value = room
        mock_broadcast = AsyncMock()

        async def _run():
            with patch(
                "backend.services.room_membership_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await membership_service.leave_room(user)

        anyio.run(_run)

        assert user.room_id is None
        mock_user_repo.save.assert_called_once_with(user)
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert call_args[0][0]["type"] == "member_left"

    def test_leave_room_not_in_room_raises(self, membership_service):
        user = MagicMock(spec=User)
        user.room_id = None

        async def _run():
            await membership_service.leave_room(user)

        with pytest.raises(EntityNotFoundException):
            anyio.run(_run)

    def test_leave_room_host_closes_room(
        self,
        membership_service,
        mock_room_service,
        mock_user_repo,
        mock_room_repo,
        room,
    ):
        host_user = MagicMock(spec=User)
        host_user.id = room.host_user_id
        host_user.username = "hostuser"
        host_user.room_id = room.id

        member = MagicMock(spec=User)
        member.id = uuid4()
        member.room_id = room.id
        room.users = [member]

        mock_room_service.get_room.return_value = room
        mock_broadcast = AsyncMock()

        async def _run():
            with patch(
                "backend.services.room_membership_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await membership_service.leave_room(host_user)

        anyio.run(_run)

        assert host_user.room_id is None
        assert member.room_id is None
        mock_room_repo.delete.assert_called_once_with(room.id)
        broadcast_calls = mock_broadcast.call_args_list
        event_types = [call[0][0]["type"] for call in broadcast_calls]
        assert "member_left" in event_types
        assert "room_closed" in event_types

    def test_leave_room_host_no_members_deletes_room(
        self,
        membership_service,
        mock_room_service,
        mock_user_repo,
        mock_room_repo,
        room,
    ):
        host_user = MagicMock(spec=User)
        host_user.id = room.host_user_id
        host_user.username = "hostuser"
        host_user.room_id = room.id
        room.users = []

        mock_room_service.get_room.return_value = room
        mock_broadcast = AsyncMock()

        async def _run():
            with patch(
                "backend.services.room_membership_service.manager"
            ) as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await membership_service.leave_room(host_user)

        anyio.run(_run)

        mock_room_repo.delete.assert_called_once_with(room.id)
