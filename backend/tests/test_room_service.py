"""Tests for RoomService logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.core.exceptions import EntityNotFoundException
from backend.db.models.room import Room
from backend.db.models.room_member import RoomMember
from backend.repositories.room_member_repo import RoomMemberRepository
from backend.repositories.room_repo import RoomRepository
from backend.schemas.room import CreateRoom, UpdateRoom
from backend.services.room_service import RoomService


@pytest.mark.anyio
class TestRoomService:
    @pytest.fixture
    def mock_room_repo(self):
        return AsyncMock(spec=RoomRepository)

    @pytest.fixture
    def mock_room_member_repo(self):
        return AsyncMock(spec=RoomMemberRepository)

    @pytest.fixture
    def room_service(self, mock_room_repo, mock_room_member_repo):
        return RoomService(mock_room_repo, mock_room_member_repo)

    async def test_get_room_success(self, room_service, mock_room_repo):
        room_id = uuid4()
        expected_room = MagicMock(spec=Room)
        mock_room_repo.get_by_id.return_value = expected_room

        result = await room_service.get_room(room_id)

        assert result == expected_room
        mock_room_repo.get_by_id.assert_called_once_with(room_id)

    async def test_get_room_not_found(self, room_service, mock_room_repo):
        room_id = uuid4()
        mock_room_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            await room_service.get_room(room_id)

    async def test_get_all_rooms(self, room_service, mock_room_repo):
        expected_rooms = [MagicMock(spec=Room), MagicMock(spec=Room)]
        mock_room_repo.get_all.return_value = expected_rooms

        result = await room_service.get_all_rooms()

        assert result == expected_rooms
        mock_room_repo.get_all.assert_called_once()

    async def test_get_host_room_success(self, room_service, mock_room_repo):
        host_id = uuid4()
        expected_room = MagicMock(spec=Room)
        mock_room_repo.get_by_host.return_value = expected_room

        result = await room_service.get_host_room(host_id)

        assert result == expected_room
        mock_room_repo.get_by_host.assert_called_once_with(host_id)

    async def test_get_host_room_not_found(self, room_service, mock_room_repo):
        host_id = uuid4()
        mock_room_repo.get_by_host.return_value = None

        with pytest.raises(EntityNotFoundException):
            await room_service.get_host_room(host_id)

    async def test_create_room_success(self, room_service, mock_room_repo):
        room_data = CreateRoom(
            host_user_id=uuid4(),
            room_name="Test Room",
            is_private=False,
            max_capacity=10
        )
        mock_room = MagicMock(spec=Room)
        mock_room_repo.create.return_value = mock_room

        with patch("backend.services.room_service.Room", return_value=mock_room):
            result = await room_service.create_room(room_data)

        assert result == mock_room
        mock_room_repo.create.assert_called_once()

    async def test_update_room_success(self, room_service, mock_room_repo):
        room_id = uuid4()
        existing_room = MagicMock(spec=Room)
        update_data = UpdateRoom(room_name="New Name")

        mock_room_repo.get_by_id.return_value = existing_room
        mock_room_repo.update.return_value = existing_room

        result = await room_service.update_room(room_id, update_data)

        assert result == existing_room
        mock_room_repo.update.assert_called_once()

    async def test_update_room_not_found(self, room_service, mock_room_repo):
        room_id = uuid4()
        mock_room_repo.get_by_id.return_value = None
        update_data = UpdateRoom(room_name="New Name")

        with pytest.raises(EntityNotFoundException):
            await room_service.update_room(room_id, update_data)

    async def test_delete_room_success(self, room_service, mock_room_repo):
        room_id = uuid4()
        mock_room_repo.get_by_id.return_value = MagicMock(spec=Room)

        await room_service.delete_room(room_id)

        mock_room_repo.delete.assert_called_once_with(room_id)

    async def test_delete_room_not_found(self, room_service, mock_room_repo):
        room_id = uuid4()
        mock_room_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            await room_service.delete_room(room_id)

    async def test_join_room_success(self, room_service, mock_room_repo, mock_room_member_repo):
        user_id = uuid4()
        room_id = uuid4()
        room = MagicMock(spec=Room)
        room.max_capacity = 5

        mock_room_repo.get_by_id.return_value = room
        mock_room_member_repo.get_member_by_user_and_room.return_value = None
        mock_room_member_repo.get_members_by_room.return_value = []

        expected_member = MagicMock(spec=RoomMember)
        mock_room_member_repo.add_member.return_value = expected_member

        result = await room_service.join_room(user_id, room_id)

        assert result == expected_member
        mock_room_member_repo.add_member.assert_called_once_with(user_id, room_id)

    async def test_join_room_already_member(self, room_service, mock_room_repo, mock_room_member_repo):
        user_id = uuid4()
        room_id = uuid4()
        room = MagicMock(spec=Room)

        mock_room_repo.get_by_id.return_value = room
        mock_room_member_repo.get_member_by_user_and_room.return_value = MagicMock(spec=RoomMember)

        with pytest.raises(ValueError, match="User is already in this room."):
            await room_service.join_room(user_id, room_id)

    async def test_join_room_full(self, room_service, mock_room_repo, mock_room_member_repo):
        user_id = uuid4()
        room_id = uuid4()
        room = MagicMock(spec=Room)
        room.max_capacity = 2

        mock_room_repo.get_by_id.return_value = room
        mock_room_member_repo.get_member_by_user_and_room.return_value = None
        mock_room_member_repo.get_members_by_room.return_value = [
            MagicMock(spec=RoomMember),
            MagicMock(spec=RoomMember),
        ]

        with pytest.raises(ValueError, match="Room is full."):
            await room_service.join_room(user_id, room_id)

    async def test_leave_room_success(self, room_service, mock_room_repo, mock_room_member_repo):
        user_id = uuid4()
        room_id = uuid4()
        room = MagicMock(spec=Room)

        mock_room_repo.get_by_id.return_value = room

        await room_service.leave_room(user_id, room_id)

        mock_room_member_repo.remove_member.assert_called_once_with(user_id, room_id)