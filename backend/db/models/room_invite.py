"""Database model representing a room invite link."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.db.models.room import Room


class RoomInvite(SQLModel, table=True):
    """A shareable invite link for joining a room without a PIN."""

    __tablename__ = "room_invites"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    room_id: UUID = Field(foreign_key="rooms.id", nullable=False)
    token: str = Field(max_length=12, unique=True, index=True, nullable=False)
    max_uses: int | None = Field(default=None, nullable=True)
    use_count: int = Field(default=0, nullable=False)
    expires_at: datetime | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    room: "Room" = Relationship(back_populates="invites")
