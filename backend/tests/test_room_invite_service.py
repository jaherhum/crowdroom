"""Tests for RoomInviteService logic."""

# ruff: noqa: D101, D102
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    InviteExpiredException,
    UserAlreadyInRoomException,
)
from backend.db.models.room import Room
from backend.db.models.room_invite import RoomInvite
from backend.db.models.user import User
from backend.repositories.room_invite_repo import RoomInviteRepository
from backend.repositories.room_repo import RoomRepository
from backend.repositories.user_repo import UserRepository
from backend.schemas.room_invite import CreateRoomInvite
from backend.services.room_invite_service import MAX_TOKEN_RETRIES, RoomInviteService
from backend.services.room_service import RoomService


class TestRoomInviteService:
    @pytest.fixture
    def mock_invite_repo(self):
        return MagicMock(spec=RoomInviteRepository)

    @pytest.fixture
    def mock_room_repo(self):
        return MagicMock(spec=RoomRepository)

    @pytest.fixture
    def mock_user_repo(self):
        return MagicMock(spec=UserRepository)

    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def invite_service(
        self, mock_invite_repo, mock_room_repo, mock_user_repo, mock_room_service
    ):
        return RoomInviteService(
            mock_invite_repo, mock_room_repo, mock_user_repo, mock_room_service
        )

    @pytest.fixture
    def host_user_id(self):
        return uuid4()

    @pytest.fixture
    def room(self, host_user_id):
        mock_room = MagicMock(spec=Room)
        mock_room.id = uuid4()
        mock_room.host_user_id = host_user_id
        mock_room.room_name = "Test Room"
        mock_room.is_private = True
        return mock_room

    # --- create_invite ---

    def test_create_invite_success(
        self, invite_service, mock_invite_repo, mock_room_service, room, host_user_id
    ):
        mock_room_service.assert_host.return_value = room
        expected_invite = MagicMock(spec=RoomInvite)
        mock_invite_repo.create.return_value = expected_invite
        data = CreateRoomInvite()

        result = invite_service.create_invite(room.id, host_user_id, data)

        assert result == expected_invite
        mock_invite_repo.create.assert_called_once()

    def test_create_invite_non_host_forbidden(
        self, invite_service, mock_room_service, room
    ):
        mock_room_service.assert_host.side_effect = ForbiddenException(
            "Only the room host can perform this action"
        )
        non_host_id = uuid4()
        data = CreateRoomInvite()

        with pytest.raises(ForbiddenException):
            invite_service.create_invite(room.id, non_host_id, data)

    def test_create_invite_room_not_found(self, invite_service, mock_room_service):
        mock_room_service.assert_host.side_effect = EntityNotFoundException(
            "Room", uuid4()
        )
        data = CreateRoomInvite()

        with pytest.raises(EntityNotFoundException):
            invite_service.create_invite(uuid4(), uuid4(), data)

    def test_create_invite_with_expiry(
        self, invite_service, mock_invite_repo, mock_room_service, room, host_user_id
    ):
        mock_room_service.assert_host.return_value = room
        created_invite = MagicMock(spec=RoomInvite)
        mock_invite_repo.create.return_value = created_invite
        data = CreateRoomInvite(expires_in_hours=24)

        invite_service.create_invite(room.id, host_user_id, data)

        call_args = mock_invite_repo.create.call_args[0][0]
        assert call_args.expires_at is not None
        expected_min = datetime.now(timezone.utc) + timedelta(hours=23, minutes=59)
        assert call_args.expires_at > expected_min

    def test_create_invite_with_max_uses(
        self, invite_service, mock_invite_repo, mock_room_service, room, host_user_id
    ):
        mock_room_service.assert_host.return_value = room
        created_invite = MagicMock(spec=RoomInvite)
        mock_invite_repo.create.return_value = created_invite
        data = CreateRoomInvite(max_uses=10)

        invite_service.create_invite(room.id, host_user_id, data)

        call_args = mock_invite_repo.create.call_args[0][0]
        assert call_args.max_uses == 10

    def test_create_invite_retries_on_token_collision(
        self, invite_service, mock_invite_repo, mock_room_service, room, host_user_id
    ):
        mock_room_service.assert_host.return_value = room
        expected_invite = MagicMock(spec=RoomInvite)
        mock_invite_repo.create.side_effect = [
            IntegrityError("", {}, None),
            IntegrityError("", {}, None),
            expected_invite,
        ]
        data = CreateRoomInvite()

        result = invite_service.create_invite(room.id, host_user_id, data)

        assert result == expected_invite
        assert mock_invite_repo.create.call_count == 3

    def test_create_invite_exhausts_retries(
        self, invite_service, mock_invite_repo, mock_room_service, room, host_user_id
    ):
        mock_room_service.assert_host.return_value = room
        mock_invite_repo.create.side_effect = IntegrityError("", {}, None)
        data = CreateRoomInvite()

        with pytest.raises(IntegrityError):
            invite_service.create_invite(room.id, host_user_id, data)

        assert mock_invite_repo.create.call_count == MAX_TOKEN_RETRIES + 1

    # --- get_invite_preview ---

    def test_get_invite_preview_success(
        self, invite_service, mock_invite_repo, mock_room_repo, room
    ):
        invite = MagicMock(spec=RoomInvite)
        invite.room_id = room.id
        invite.expires_at = None
        invite.max_uses = None
        invite.use_count = 0
        mock_invite_repo.get_by_token.return_value = invite
        mock_room_repo.get_by_id.return_value = room

        result = invite_service.get_invite_preview("abc123token0")

        assert result.room_id == room.id
        assert result.room_name == room.room_name
        assert result.is_private == room.is_private
        assert result.host_user_id == room.host_user_id

    def test_get_invite_preview_not_found(self, invite_service, mock_invite_repo):
        mock_invite_repo.get_by_token.return_value = None

        with pytest.raises(EntityNotFoundException):
            invite_service.get_invite_preview("nonexistent00")

    def test_get_invite_preview_expired(self, invite_service, mock_invite_repo):
        invite = MagicMock(spec=RoomInvite)
        invite.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        invite.max_uses = None
        invite.use_count = 0
        mock_invite_repo.get_by_token.return_value = invite

        with pytest.raises(InviteExpiredException):
            invite_service.get_invite_preview("expiredtoken")

    def test_get_invite_preview_exhausted(self, invite_service, mock_invite_repo):
        invite = MagicMock(spec=RoomInvite)
        invite.expires_at = None
        invite.max_uses = 5
        invite.use_count = 5
        mock_invite_repo.get_by_token.return_value = invite

        with pytest.raises(InviteExpiredException):
            invite_service.get_invite_preview("useduptoken0")

    # --- join_via_invite ---

    def test_join_via_invite_success(
        self, invite_service, mock_invite_repo, mock_room_repo, mock_user_repo, room
    ):
        invite = MagicMock(spec=RoomInvite)
        invite.room_id = room.id
        invite.expires_at = None
        invite.max_uses = None
        invite.use_count = 0
        mock_invite_repo.get_by_token.return_value = invite
        mock_room_repo.get_by_id.return_value = room

        user = MagicMock(spec=User)
        user.room_id = None
        mock_user_repo.save.return_value = user

        result = invite_service.join_via_invite("validtoken00", user)

        assert result.room_id == room.id
        assert result.room_name == room.room_name
        assert user.room_id == room.id
        mock_user_repo.save.assert_called_once_with(user)
        mock_invite_repo.increment_use_count.assert_called_once_with(invite)

    def test_join_via_invite_expired(self, invite_service, mock_invite_repo):
        invite = MagicMock(spec=RoomInvite)
        invite.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        invite.max_uses = None
        invite.use_count = 0
        mock_invite_repo.get_by_token.return_value = invite

        user = MagicMock(spec=User)

        with pytest.raises(InviteExpiredException):
            invite_service.join_via_invite("expiredtoken", user)

    def test_join_via_invite_exhausted(self, invite_service, mock_invite_repo):
        invite = MagicMock(spec=RoomInvite)
        invite.expires_at = None
        invite.max_uses = 3
        invite.use_count = 3
        mock_invite_repo.get_by_token.return_value = invite

        user = MagicMock(spec=User)

        with pytest.raises(InviteExpiredException):
            invite_service.join_via_invite("useduptoken0", user)

    def test_join_via_invite_not_found(self, invite_service, mock_invite_repo):
        mock_invite_repo.get_by_token.return_value = None
        user = MagicMock(spec=User)

        with pytest.raises(EntityNotFoundException):
            invite_service.join_via_invite("nonexistent0", user)

    def test_join_via_invite_user_already_in_room(
        self, invite_service, mock_invite_repo, mock_room_repo, mock_user_repo, room
    ):
        invite = MagicMock(spec=RoomInvite)
        invite.room_id = room.id
        invite.expires_at = None
        invite.max_uses = None
        invite.use_count = 0
        mock_invite_repo.get_by_token.return_value = invite
        mock_room_repo.get_by_id.return_value = room

        user = MagicMock(spec=User)
        user.room_id = uuid4()  # already in another room
        mock_user_repo.save.return_value = user

        with pytest.raises(UserAlreadyInRoomException):
            invite_service.join_via_invite("validtoken00", user)

    # --- list_invites ---

    def test_list_invites_success(
        self, invite_service, mock_invite_repo, mock_room_service, room, host_user_id
    ):
        mock_room_service.assert_host.return_value = room
        invites = [MagicMock(spec=RoomInvite), MagicMock(spec=RoomInvite)]
        mock_invite_repo.get_by_room.return_value = invites

        result = invite_service.list_invites(room.id, host_user_id)

        assert result == invites
        mock_invite_repo.get_by_room.assert_called_once_with(room.id)

    def test_list_invites_non_host_forbidden(
        self, invite_service, mock_room_service, room
    ):
        mock_room_service.assert_host.side_effect = ForbiddenException(
            "Only the room host can perform this action"
        )
        non_host_id = uuid4()

        with pytest.raises(ForbiddenException):
            invite_service.list_invites(room.id, non_host_id)

    # --- revoke_invite ---

    def test_revoke_invite_success(
        self, invite_service, mock_invite_repo, mock_room_service, room, host_user_id
    ):
        mock_room_service.assert_host.return_value = room
        invite = MagicMock(spec=RoomInvite)
        invite.room_id = room.id
        invite_id = uuid4()
        mock_invite_repo.get_by_id.return_value = invite

        invite_service.revoke_invite(room.id, invite_id, host_user_id)

        mock_invite_repo.delete.assert_called_once_with(invite_id)

    def test_revoke_invite_non_host_forbidden(
        self, invite_service, mock_room_service, room
    ):
        mock_room_service.assert_host.side_effect = ForbiddenException(
            "Only the room host can perform this action"
        )
        non_host_id = uuid4()

        with pytest.raises(ForbiddenException):
            invite_service.revoke_invite(room.id, uuid4(), non_host_id)

    def test_revoke_invite_not_found(
        self, invite_service, mock_invite_repo, mock_room_service, room, host_user_id
    ):
        mock_room_service.assert_host.return_value = room
        mock_invite_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            invite_service.revoke_invite(room.id, uuid4(), host_user_id)

    def test_revoke_invite_wrong_room(
        self, invite_service, mock_invite_repo, mock_room_service, room, host_user_id
    ):
        mock_room_service.assert_host.return_value = room
        invite = MagicMock(spec=RoomInvite)
        invite.room_id = uuid4()  # different room
        mock_invite_repo.get_by_id.return_value = invite

        with pytest.raises(ForbiddenException):
            invite_service.revoke_invite(room.id, uuid4(), host_user_id)


class TestInviteTokenGeneration:
    def test_token_length(self):
        from backend.core.invite_token import generate_invite_token

        token = generate_invite_token()
        assert len(token) == 12

    def test_token_charset(self):
        from backend.core.invite_token import (
            INVITE_TOKEN_CHARSET,
            generate_invite_token,
        )

        token = generate_invite_token()
        for char in token:
            assert char in INVITE_TOKEN_CHARSET

    def test_tokens_unique(self):
        from backend.core.invite_token import generate_invite_token

        tokens = {generate_invite_token() for _ in range(100)}
        assert len(tokens) == 100
