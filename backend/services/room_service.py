"""Service for managing chat rooms and their associated data."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from backend.api.websocket import manager
from backend.core.exceptions import (
    EntityExistsException,
    EntityNotFoundException,
    ForbiddenException,
)
from backend.core.room_code import generate_room_code
from backend.core.security import SecurityService
from backend.db.models.room import Room
from backend.repositories.room_repo import RoomRepository
from backend.schemas.room import CreateRoom, UpdateRoom

MAX_CODE_RETRIES = 5


class RoomService:
    """Service for managing chat rooms and their associated data."""

    def __init__(
        self, room_repo: RoomRepository, security_service: SecurityService
    ) -> None:
        """Initialize the RoomService with its dependencies.

        Args:
            room_repo: Repository for all room data operations.
            security_service: Service for PIN hashing and verification.
        """
        self._room_repo = room_repo
        self._security_service = security_service

    def assert_host(self, room_id: UUID, user_id: UUID) -> Room:
        """Verify user is the host of the given room.

        Args:
            room_id: The room to check.
            user_id: The user to verify as host.

        Returns:
            The Room instance if user is host.

        Raises:
            EntityNotFoundException: If room does not exist.
            ForbiddenException: If user is not the room host.
        """
        room = self.get_room(room_id)
        if room.host_user_id != user_id:
            raise ForbiddenException("Only the room host can perform this action")
        return room

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
        """Retrieve all publicly listable rooms.

        Returns:
            list[Room]: Rooms that are public or private-but-visible.
        """
        return self._room_repo.get_listed_rooms()

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

    def get_host_rooms(self, host_id: UUID) -> list[Room]:
        """Retrieve all rooms owned by a host, regardless of visibility.

        Args:
            host_id: The unique identifier of the host user.

        Returns:
            The host's rooms (empty list if none found).
        """
        room = self._room_repo.get_by_host(host_id)
        if room is None:
            return []
        return [room]

    def get_room_by_code(self, room_code: str) -> Room:
        """Retrieve a room by its unique sharing code.

        Args:
            room_code: The 6-character room code.

        Returns:
            Room: The room instance.

        Raises:
            EntityNotFoundException: If no room matches the code.
        """
        room = self._room_repo.get_by_code(room_code.upper())
        if not room:
            raise EntityNotFoundException("Room", room_code)
        return room

    def create_room(self, room_data: CreateRoom) -> Room:
        """Create a new room, hashing the PIN if provided.

        Args:
            room_data: The schema containing creation details.

        Returns:
            The newly created room.

        Raises:
            EntityExistsException: If the host already owns a room (one room
                per host).
            IntegrityError: If room code generation exhausts all retries.
        """
        if self._room_repo.get_by_host(room_data.host_user_id) is not None:
            raise EntityExistsException("Room")

        pin_hash = None
        if room_data.pin is not None:
            pin_hash = self._security_service.generate_password_hash(room_data.pin)

        for attempt in range(MAX_CODE_RETRIES + 1):
            settings = room_data.settings.model_dump()
            new_room = Room(
                host_user_id=room_data.host_user_id,
                room_name=room_data.room_name,
                is_private=room_data.is_private,
                pin_hash=pin_hash,
                is_visible=room_data.is_visible,
                room_code=generate_room_code(),
                settings=settings,
            )
            try:
                return self._room_repo.create(new_room)
            except IntegrityError:
                if attempt == MAX_CODE_RETRIES:
                    raise

    async def update_room(self, room_id: UUID, room_data: UpdateRoom) -> Room:
        """Update an existing room.

        Handles PIN hashing on change and enforces that making a room
        private requires a PIN in the same request if none exists.

        Args:
            room_id: The unique identifier of the room to update.
            room_data: The schema containing update details.

        Returns:
            The updated room instance.

        Raises:
            EntityNotFoundException: If the room is not found.
            ValueError: If making room private without providing a PIN.
        """
        existing_room = self.get_room(room_id)
        data = room_data.model_dump(exclude_unset=True)

        if "pin" in data:
            raw_pin = data.pop("pin")
            if raw_pin is not None:
                data["pin_hash"] = self._security_service.generate_password_hash(
                    raw_pin
                )
            else:
                data["pin_hash"] = None

        is_becoming_private = data.get("is_private") is True
        has_no_pin = "pin_hash" not in data and existing_room.pin_hash is None
        if is_becoming_private and has_no_pin:
            raise ValueError("PIN required when making room private")

        updated_room = self._room_repo.update(room_id, data)
        if not updated_room:
            raise EntityNotFoundException("Room", room_id)

        broadcast_payload = {key: val for key, val in data.items() if key != "pin_hash"}

        await manager.broadcast(
            {"type": "settings_updated", "payload": broadcast_payload}, str(room_id)
        )

        return updated_room

    def verify_pin(self, room_id: UUID, pin: str) -> bool:
        """Verify a PIN against a room's stored hash.

        Args:
            room_id: The unique identifier of the room to verify against.
            pin: The raw PIN string to check.

        Returns:
            True if PIN matches or room has no PIN set, False otherwise.

        Raises:
            EntityNotFoundException: If the room is not found.
        """
        room = self.get_room(room_id)
        if not room.pin_hash:
            return True
        return self._security_service.verify_password(pin, room.pin_hash)

    def delete_room(self, room_id: UUID) -> None:
        """Delete a room from the system.

        Args:
            room_id (UUID): The unique identifier of the room to delete.

        Raises:
            EntityNotFoundException: If the room is not found.
        """
        self.get_room(room_id)
        self._room_repo.delete(room_id)
