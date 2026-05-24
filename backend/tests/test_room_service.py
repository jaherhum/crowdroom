"""Tests for RoomService logic."""

# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest

from backend.api.websocket import manager
from backend.core.exceptions import EntityNotFoundException
from backend.core.security import SecurityService
from backend.db.models.room import Room
from backend.repositories.room_repo import RoomRepository
from backend.schemas.room import CreateRoom, UpdateRoom
from backend.services.room_service import RoomService


class TestRoomService:
    @pytest.fixture
    def mock_room_repo(self):
        return MagicMock(spec=RoomRepository)

    @pytest.fixture
    def mock_security_service(self):
        mock = MagicMock(spec=SecurityService)
        mock.generate_password_hash.return_value = "hashed_pin_value"
        mock.verify_password.return_value = True
        return mock

    @pytest.fixture
    def room_service(self, mock_room_repo, mock_security_service):
        return RoomService(mock_room_repo, mock_security_service)

    def test_get_room_success(self, room_service, mock_room_repo):
        room_id = uuid4()
        expected_room = MagicMock(spec=Room)
        mock_room_repo.get_by_id.return_value = expected_room

        result = room_service.get_room(room_id)

        assert result == expected_room
        mock_room_repo.get_by_id.assert_called_once_with(room_id)

    def test_get_room_not_found(self, room_service, mock_room_repo):
        room_id = uuid4()
        mock_room_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            room_service.get_room(room_id)

    def test_get_all_rooms(self, room_service, mock_room_repo):
        public_room = MagicMock(spec=Room, is_private=False, is_visible=True)
        private_visible = MagicMock(spec=Room, is_private=True, is_visible=True)
        private_invisible = MagicMock(spec=Room, is_private=True, is_visible=False)
        mock_room_repo.get_all.return_value = [
            public_room, private_visible, private_invisible
        ]

        result = room_service.get_all_rooms()

        assert public_room in result
        assert private_visible in result
        assert private_invisible not in result
        mock_room_repo.get_all.assert_called_once()

    def test_get_host_room_success(self, room_service, mock_room_repo):
        host_id = uuid4()
        expected_room = MagicMock(spec=Room)
        mock_room_repo.get_by_host.return_value = expected_room

        result = room_service.get_host_room(host_id)

        assert result == expected_room
        mock_room_repo.get_by_host.assert_called_once_with(host_id)

    def test_get_host_room_not_found(self, room_service, mock_room_repo):
        host_id = uuid4()
        mock_room_repo.get_by_host.return_value = None

        with pytest.raises(EntityNotFoundException):
            room_service.get_host_room(host_id)

    def test_create_room_success(self, room_service, mock_room_repo):
        room_data = CreateRoom(
            host_user_id=uuid4(), room_name="Test Room", is_private=False
        )
        mock_room = MagicMock(spec=Room)
        mock_room_repo.create.return_value = mock_room

        with patch("backend.services.room_service.Room", return_value=mock_room):
            result = room_service.create_room(room_data)

        assert result == mock_room
        mock_room_repo.create.assert_called_once()

    def test_update_room_success(self, room_service, mock_room_repo):
        room_id = uuid4()
        existing_room = MagicMock(spec=Room, pin_hash="some_hash")
        update_data = UpdateRoom(room_name="New Name")

        mock_room_repo.get_by_id.return_value = existing_room
        mock_room_repo.update.return_value = existing_room

        mock_broadcast = AsyncMock()
        results = {}

        async def _run():
            with patch.object(manager, "broadcast", new=mock_broadcast):
                results["room"] = await room_service.update_room(room_id, update_data)

        anyio.run(_run)

        assert results["room"] == existing_room
        mock_room_repo.update.assert_called_once()
        mock_broadcast.assert_called_once()

    def test_update_room_not_found(self, room_service, mock_room_repo):
        room_id = uuid4()
        mock_room_repo.get_by_id.return_value = None
        update_data = UpdateRoom(room_name="New Name")

        async def _run():
            await room_service.update_room(room_id, update_data)

        with pytest.raises(EntityNotFoundException):
            anyio.run(_run)

    def test_delete_room_success(self, room_service, mock_room_repo):
        room_id = uuid4()
        mock_room_repo.get_by_id.return_value = MagicMock(spec=Room)

        room_service.delete_room(room_id)

        mock_room_repo.delete.assert_called_once_with(room_id)

    def test_delete_room_not_found(self, room_service, mock_room_repo):
        room_id = uuid4()
        mock_room_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            room_service.delete_room(room_id)

    def test_create_private_room_hashes_pin(
        self, room_service, mock_room_repo, mock_security_service
    ):
        room_data = CreateRoom(
            host_user_id=uuid4(), room_name="Secret", is_private=True, pin="1234"
        )
        mock_room_repo.create.return_value = MagicMock(spec=Room)

        with patch("backend.services.room_service.Room") as mock_room_cls:
            mock_room_cls.return_value = MagicMock(spec=Room)
            room_service.create_room(room_data)

        mock_security_service.generate_password_hash.assert_called_once_with("1234")
        mock_room_cls.assert_called_once()
        call_kwargs = mock_room_cls.call_args[1]
        assert call_kwargs["pin_hash"] == "hashed_pin_value"

    def test_create_public_room_no_pin_hash(
        self, room_service, mock_room_repo, mock_security_service
    ):
        room_data = CreateRoom(
            host_user_id=uuid4(), room_name="Open", is_private=False
        )
        mock_room_repo.create.return_value = MagicMock(spec=Room)

        with patch("backend.services.room_service.Room") as mock_room_cls:
            mock_room_cls.return_value = MagicMock(spec=Room)
            room_service.create_room(room_data)

        mock_security_service.generate_password_hash.assert_not_called()
        call_kwargs = mock_room_cls.call_args[1]
        assert call_kwargs["pin_hash"] is None

    def test_create_private_room_without_pin_rejected(self):
        with pytest.raises(ValueError, match="private room needs a PIN"):
            CreateRoom(
                host_user_id=uuid4(), room_name="Bad", is_private=True
            )

    def test_create_public_room_with_pin_rejected(self):
        with pytest.raises(ValueError, match="public room can't have a PIN"):
            CreateRoom(
                host_user_id=uuid4(), room_name="Bad", is_private=False, pin="1234"
            )

    def test_pin_format_invalid(self):
        with pytest.raises(ValueError, match="4-6 digits"):
            CreateRoom(
                host_user_id=uuid4(), room_name="Bad", is_private=True, pin="abc"
            )

        with pytest.raises(ValueError, match="4-6 digits"):
            CreateRoom(
                host_user_id=uuid4(), room_name="Bad", is_private=True, pin="123"
            )

        with pytest.raises(ValueError, match="4-6 digits"):
            CreateRoom(
                host_user_id=uuid4(), room_name="Bad", is_private=True, pin="1234567"
            )

    def test_update_room_hashes_new_pin(
        self, room_service, mock_room_repo, mock_security_service
    ):
        room_id = uuid4()
        existing_room = MagicMock(spec=Room, pin_hash="old_hash")
        update_data = UpdateRoom(pin="5678")

        mock_room_repo.get_by_id.return_value = existing_room
        mock_room_repo.update.return_value = existing_room

        mock_broadcast = AsyncMock()

        async def _run():
            with patch.object(manager, "broadcast", new=mock_broadcast):
                await room_service.update_room(room_id, update_data)

        anyio.run(_run)

        mock_security_service.generate_password_hash.assert_called_once_with("5678")
        update_call_data = mock_room_repo.update.call_args[0][1]
        assert update_call_data["pin_hash"] == "hashed_pin_value"
        assert "pin" not in update_call_data

    def test_update_room_clears_pin(
        self, room_service, mock_room_repo, mock_security_service
    ):
        room_id = uuid4()
        existing_room = MagicMock(spec=Room, pin_hash="old_hash")
        update_data = UpdateRoom(pin=None)

        mock_room_repo.get_by_id.return_value = existing_room
        mock_room_repo.update.return_value = existing_room

        mock_broadcast = AsyncMock()

        async def _run():
            with patch.object(manager, "broadcast", new=mock_broadcast):
                await room_service.update_room(room_id, update_data)

        anyio.run(_run)

        mock_security_service.generate_password_hash.assert_not_called()
        update_call_data = mock_room_repo.update.call_args[0][1]
        assert update_call_data["pin_hash"] is None

    def test_update_room_private_without_pin_rejected(
        self, room_service, mock_room_repo
    ):
        room_id = uuid4()
        existing_room = MagicMock(spec=Room, pin_hash=None)
        update_data = UpdateRoom(is_private=True)

        mock_room_repo.get_by_id.return_value = existing_room

        async def _run():
            await room_service.update_room(room_id, update_data)

        with pytest.raises(ValueError, match="PIN required"):
            anyio.run(_run)

    def test_verify_pin_correct(
        self, room_service, mock_room_repo, mock_security_service
    ):
        room_id = uuid4()
        mock_room = MagicMock(spec=Room, pin_hash="hashed")
        mock_room_repo.get_by_id.return_value = mock_room
        mock_security_service.verify_password.return_value = True

        assert room_service.verify_pin(room_id, "1234") is True
        mock_security_service.verify_password.assert_called_once_with("1234", "hashed")

    def test_verify_pin_wrong(
        self, room_service, mock_room_repo, mock_security_service
    ):
        room_id = uuid4()
        mock_room = MagicMock(spec=Room, pin_hash="hashed")
        mock_room_repo.get_by_id.return_value = mock_room
        mock_security_service.verify_password.return_value = False

        assert room_service.verify_pin(room_id, "0000") is False

    def test_verify_pin_no_pin_set(self, room_service, mock_room_repo):
        room_id = uuid4()
        mock_room = MagicMock(spec=Room, pin_hash=None)
        mock_room_repo.get_by_id.return_value = mock_room

        assert room_service.verify_pin(room_id, "anything") is True
