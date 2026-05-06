"""Tests for RoomService logic."""
# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest

from backend.api.websocket import manager
from backend.core.exceptions import EntityNotFoundException
from backend.db.models.room import Room
from backend.repositories.room_repo import RoomRepository
from backend.schemas.room import CreateRoom, UpdateRoom
from backend.services.room_service import RoomService


class TestRoomService:
    @pytest.fixture
    def mock_room_repo(self):
        return MagicMock(spec=RoomRepository)

    @pytest.fixture
    def room_service(self, mock_room_repo):
        return RoomService(mock_room_repo)

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
        expected_rooms = [MagicMock(spec=Room), MagicMock(spec=Room)]
        mock_room_repo.get_all.return_value = expected_rooms

        result = room_service.get_all_rooms()

        assert result == expected_rooms
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
            host_user_id=uuid4(),
            room_name="Test Room",
            is_private=False
        )
        mock_room = MagicMock(spec=Room)
        mock_room_repo.create.return_value = mock_room

        with patch("backend.services.room_service.Room", return_value=mock_room):
            result = room_service.create_room(room_data)

        assert result == mock_room
        mock_room_repo.create.assert_called_once()

    def test_update_room_success(self, room_service, mock_room_repo):
        room_id = uuid4()
        existing_room = MagicMock(spec=Room)
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
