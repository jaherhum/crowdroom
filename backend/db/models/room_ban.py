"""Database model representing a user banned from a room."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.db.models.room import Room
    from backend.db.models.user import User


class RoomBan(SQLModel, table=True):
    """A record blocking a user from re-entering a specific room.

    Created when a host bans a user. While a matching row exists, the user is
    rejected at join time. Removing the row (unban) restores access.

    Attributes:
        id (UUID): Primary key.
        room_id (UUID): The room the ban applies to.
        user_id (UUID): The banned user.
        created_at (datetime): When the ban was issued.
    """

    __tablename__ = "room_bans"
    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_room_ban"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    room_id: UUID = Field(foreign_key="rooms.id", nullable=False, index=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    room: "Room" = Relationship(back_populates="bans")
    user: "User" = Relationship()
