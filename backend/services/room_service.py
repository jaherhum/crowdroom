"""Service for managing chat rooms and their associated data."""

from typing import List
from uuid import UUID

from backend.api.websocket import manager
from backend.core.exceptions import EntityNotFoundException
from backend.db.models.room import Room
from backend.db.models.room_member import RoomMember
from backend.repositories.room_member_repo import RoomMemberRepository
from backend.repositories.room_repo import RoomRepository
from backend.schemas.room import CreateRoom, UpdateRoom


class RoomService:
    """Service for managing chat rooms and their associated data."""

    def __init__(
        self,
        room_repo: RoomRepository,
        room_member_repo: RoomMemberRepository
    ) -> None:
        """Initialize the RoomService with repositories.

        Args:
            room_repo (RoomRepository): Repository for room operations.
            room_member_repo (RoomMemberRepository): Repository for
                membership operations.
        """
        self._room_repo = room_repo
        self._room_member_repo = room_member_repo

    async def get_room(self, room_id: UUID) -> Room:
        """Retrieve a specific room by its ID.

        Args:
            room_id (UUID): The unique identifier of the room.

        Returns:
            Room: The room instance.

        Raises:
            EntityNotFoundException: If the room is not found.
        """
        room = await self._room_repo.get_by_id(room_id)
        if not room:
            raise EntityNotFoundException("Room", room_id)
        return room

    async def get_all_rooms(self) -> List[Room]:
        """Retrieve all rooms.

        Returns:
            List[Room]: A list of all rooms.
        """
        rooms = await self._room_repo.get_all()
        return rooms

    async def get_host_room(self, host_id: UUID) -> Room:
        """Retrieve the room owned by a specific host.

        Args:
            host_id (UUID): The unique identifier of the host.

        Returns:
            Room: The room instance.

        Raises:
            EntityNotFoundException: If no room is found for the host.
        """
        room = await self._room_repo.get_by_host(host_id)
        if not room:
            raise EntityNotFoundException("Room", str(host_id))
        return room

    async def create_room(self, room_data: CreateRoom) -> Room:
        """Create a new room.

        Args:
            room_data (CreateRoom): The schema containing creation details.

        Returns:
            Room: The newly created room.
        """
        new_room = Room(
            host_user_id=room_data.host_user_id,
            room_name=room_data.room_name,
            is_private=room_data.is_private,
            max_capacity=getattr(room_data, 'max_capacity', 0)
        )

        return await self._room_repo.create(new_room)

    async def update_room(self, room_id: UUID, room_data: UpdateRoom) -> Room:
        """Update an existing room.

        Args:
            room_id (UUID): The unique identifier of the room to update.
            room_data (UpdateRoom): The schema containing update details.

        Returns:
            Room: The updated room instance.

        Raises:
            EntityNotFoundException: If the room is not found.
        """
        await self.get_room(room_id)
        data = room_data.model_dump(exclude_unset=True)
        updated_room = await self._room_repo.update(room_id, data)
        if not updated_room:
            raise EntityNotFoundException("Room", room_id)

        # Broadcast settings update
        await manager.broadcast(
            {
                "type": "settings_updated",
                "payload": data
            },
            str(room_id)
        )

        return updated_room

    async def delete_room(self, room_id: UUID) -> None:
        """Delete a room from the system.

        Args:
            room_id (UUID): The unique identifier of the room to delete.

        Raises:
            EntityNotFoundException: If the room is not found.
        """
        await self.get_room(room_id)
        await self._room_repo.delete(room_id)

    async def join_room(self, user_id: UUID, room_id: UUID) -> RoomMember:
        """Join a room.

        Args:
            user_id (UUID): The ID of the user joining.
            room_id (UUID): The ID of the room to join.

        Returns:
            RoomMember: The newly created membership.

        Raises:
            EntityNotFoundException: If the room is not found.
            ValueError: If the room is full or user is already a member.
        """
        room = await self.get_room(room_id)

        # Check if user is already a member
        existing_member = await self._room_member_repo.get_member_by_user_and_room(
            user_id, room_id
        )
        if existing_member:
            raise ValueError("User is already in this room.")

        # Check capacity
        members = await self._room_member_repo.get_members_by_room(room_id)
        if 0 < room.max_capacity <= len(members):
            raise ValueError("Room is full.")

        new_member = await self._room_member_repo.add_member(user_id, room_id)

        # Broadcast join event
        await manager.broadcast(
            {
                "type": "member_joined",
                "payload": {"user_id": str(user_id)}
            },
            str(room_id)
        )

        return new_member

    async def leave_room(self, user_id: UUID, room_id: UUID) -> None:
        """Leave a room.

        Args:
            user_id (UUID): The ID of the user leaving.
            room_id (UUID): The ID of the room to leave.

        Raises:
            EntityNotFoundException: If the room is not found.
        """
        await self.get_room(room_id)
        await self._room_member_repo.remove_member(user_id, room_id)

        # Broadcast leave event
        await manager.broadcast(
            {
                "type": "member_left",
                "payload": {"user_id": str(user_id)}
            },
            str(room_id)
        )
