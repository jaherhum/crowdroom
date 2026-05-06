"""Repository for Room data access."""
from uuid import UUID

from sqlmodel import Session as DBSession, select

from backend.db.models.room import Room


class RoomRepository:
    """Handles database operations for Rooms."""

    def __init__(self, session: DBSession):
        """Initializes the repository with a database session."""
        self._session = session

    def create(self, room: Room) -> Room:
        """Creates a new room in the database.

        Args:
            room (Room): The room instance to create.

        Returns:
            Room: The created room.
        """
        self._session.add(room)
        self._session.commit()
        self._session.refresh(room)
        return room

    def get_by_id(self, room_id: UUID) -> Room | None:
        """Retrieves a room by its ID.

        Args:
            room_id (UUID): The unique identifier of the room.

        Returns:
            Room | None: The room instance if found, otherwise None.
        """
        return self._session.get(Room, room_id)

    def get_all(self) -> list[Room]:
        """Retrieves all rooms in the database.

        Returns:
            list[Room]: A list of all rooms.
        """
        return self._session.exec(select(Room)).all()

    def get_by_host(self, host_user_id: UUID) -> Room | None:
        """Retrieves the room owned by a specific host.

        Args:
            host_user_id (UUID): The unique identifier of the host user.

        Returns:
            Room | None: The room instance if found, otherwise None.
        """
        return self._session.exec(
            select(Room).where(Room.host_user_id == host_user_id)
        ).first()

    def delete(self, room_id: UUID) -> None:
        """Deletes a room from the database.

        Args:
            room_id (UUID): The unique identifier of the room to delete.
        """
        room = self.get_by_id(room_id)
        if room:
            self._session.delete(room)
            self._session.commit()

    def update(self, room_id: UUID, update_data: dict) -> Room | None:
        """Updates an existing room with the provided data.

        Args:
            room_id (UUID): The unique identifier of the room.
            update_data (dict): A dictionary containing the fields to update.

        Returns:
            Room | None: The updated room instance if found, otherwise None.
        """
        room = self.get_by_id(room_id)
        if room:
            for key, value in update_data.items():
                if hasattr(room, key):
                    setattr(room, key, value)

            self._session.add(room)
            self._session.commit()
            self._session.refresh(room)
            return room
        return None
