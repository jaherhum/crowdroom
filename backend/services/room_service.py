"""Service for managing chat rooms and their associated data."""

from uuid import UUID

from backend.api.websocket import manager
from backend.core.exceptions import EntityNotFoundException
from backend.db.models.room import Room
from backend.repositories.room_repo import RoomRepository
from backend.schemas.room import CreateRoom, UpdateRoom


class RoomService:
    """Service for managing chat rooms and their associated data."""

    def __init__(self, room_repo: RoomRepository) -> None:
        """Initialize the RoomService with its repository.

        Args:
            room_repo: Repository for all room data operations.
        """
        self._room_repo = room_repo

    def get_room(self, room_id: UUID) -> Room:
        """Retrieve a specific room by its ID.

        Args:
            room_id (UUID): The unique identifier of the room.

        Returns:
            Room: The room instance.

        Raises:
            EntityNotFoundException: If the room is not found.
        """
        room = self._room_repo.get_by_id(room_id)
        if not room:
            raise EntityNotFoundException("Room", room_id)
        return room

    def get_all_rooms(self) -> list[Room]:
        """Retrieve all rooms.

        Returns:
            list[Room]: A list of all rooms.
        """
        rooms = self._room_repo.get_all()
        return rooms

    def get_host_room(self, host_id: UUID) -> Room:
        """Retrieve the room owned by a specific host.

        Args:
            host_id (UUID): The unique identifier of the host.

        Returns:
            Room: The room instance.

        Raises:
            EntityNotFoundException: If no room is found for the host.
        """
        room = self._room_repo.get_by_host(host_id)
        if not room:
            raise EntityNotFoundException("Room", str(host_id))
        return room

    def create_room(self, room_data: CreateRoom) -> Room:
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
        )

        return self._room_repo.create(new_room)

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
        self.get_room(room_id)
        data = room_data.model_dump(exclude_unset=True)
        updated_room = self._room_repo.update(room_id, data)
        if not updated_room:
            raise EntityNotFoundException("Room", room_id)

        # Broadcast settings update
        await manager.broadcast(
            {"type": "settings_updated", "payload": data}, str(room_id)
        )

        return updated_room

    def delete_room(self, room_id: UUID) -> None:
        """Delete a room from the system.

        Args:
            room_id (UUID): The unique identifier of the room to delete.

        Raises:
            EntityNotFoundException: If the room is not found.
        """
        self.get_room(room_id)
        self._room_repo.delete(room_id)
