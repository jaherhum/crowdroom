"""Database model representing a virtual meeting room."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.db.models.room_member import RoomMember
    from backend.db.models.session import Session
    from backend.db.models.user import User


class Room(SQLModel, table=True):
    """Database model representing a virtual meeting room.

    A Room acts as the primary container for music sessions and users.
    It can be public or private and holds specific configuration settings.

    Attributes:
        id (UUID): Primary key, unique identifier for the room.
        host_user_id (UUID): Foreign key referencing the user who owns/created the room.
        room_name (str): Display name of the room.
        max_capacity (int): Maximum capacity of the room.
        is_private (bool): Flag indicating if the room is private.
        settings (dict): JSON-based dictionary for storing configurations.
        user (User): Relationship to the host user.
        session (Optional[Session]): Relationship to the active session.
        members (list[RoomMember]): List of users currently in the room.
    """

    __tablename__ = "rooms"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    host_user_id: UUID = Field(foreign_key="users.id", nullable=False, unique=True)
    room_name: str = Field(max_length=255, nullable=False)
    max_capacity: int = Field(default=0, nullable=False)
    is_private: bool = Field(default=False, nullable=False)
    settings: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )

    # Relations
    user: "User" = Relationship(back_populates="room")
    session: Optional["Session"] = Relationship(back_populates="room")
    members: list["RoomMember"] = Relationship(back_populates="room")
