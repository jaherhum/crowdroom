"""Database model representing a virtual meeting room."""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
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
        is_private (bool): Flag indicating if the room is private.
        settings (dict): JSON-based dictionary for storing configurations.
        users (list[User]): List of users currently in the room.
        session (Optional[Session]): Relationship to the active session.
    """

    __tablename__ = "rooms"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    host_user_id: UUID = Field(foreign_key="users.id", nullable=False)
    room_name: str = Field(max_length=255, nullable=False)
    is_private: bool = Field(default=False, nullable=False)
    pin_hash: str | None = Field(default=None, max_length=255, nullable=True)
    is_visible: bool = Field(default=True, nullable=False)
    settings: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )

    # Relations
    users: Mapped[list["User"]] = Relationship(
        back_populates="room",
        sa_relationship_kwargs={"foreign_keys": "[User.room_id]"},
    )
    session: "Session" = Relationship(back_populates="room")
