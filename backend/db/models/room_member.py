"""Database model representing a user's membership in a room."""
from __future__ import annotations
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.db.models.room import Room
    from backend.db.models.user import User


class RoomMember(SQLModel, table=True):
    """Database model representing a user's membership in a room.

    Attributes:
        id (UUID): Primary key.
        user_id (UUID): Foreign key referencing the User.
        room_id (UUID): Foreign key referencing the Room.
        joined_at (datetime): Timestamp when the user joined the room.
        user (User): Relationship to the User.
        room (Room): Relationship to the Room.
    """

    __tablename__ = "room_members"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, unique=True)
    room_id: UUID = Field(foreign_key="rooms.id", nullable=False)

    # Relations
    user: "User" = Relationship(back_populates="room_memberships")
    room: "Room" = Relationship(back_populates="members")