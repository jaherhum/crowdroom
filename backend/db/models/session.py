"""Database model representing an active music playback session."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from backend.db.models.enum import ItemStatus, StreamingPlatforms

if TYPE_CHECKING:
    from backend.db.models.queue_history import QueueHistory
    from backend.db.models.queue_item import QueueItem
    from backend.db.models.room import Room


class Session(SQLModel, table=True):
    """Database model representing an active music playback session.

    A Session is tied to a Room and tracks the current state of playback,
    including the platform being used and the song currently playing.

    Attributes:
        id (UUID): Primary key, unique identifier for the session.
        room_id (UUID): Foreign key referencing the Room this session belongs to.
        current_platform (StreamingPlatforms): The streaming service in use.
        current_song_id (str, optional): The external ID of the song being played.
        last_updated (datetime): Timestamp of the last session state update.
        room (Room): Relationship to the parent Room.
        queue_items (list[QueueItem]): List of items currently in the queue.
        queue_histories (list[QueueHistory]): List of played/skipped songs.
    """

    __tablename__ = "sessions"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    room_id: UUID = Field(foreign_key="rooms.id", nullable=False, unique=True)
    current_platform: StreamingPlatforms = Field(
        default=StreamingPlatforms.SPOTIFY, nullable=False
    )
    current_song_id: str | None = Field(default=None, nullable=True)

    last_updated: datetime = Field(default_factory=datetime.now, nullable=False)
    playback_status: ItemStatus | None = Field(
        default=None, sa_column=sa.Column(sa.Enum(ItemStatus), nullable=True)
    )
    playback_position_ms: int | None = Field(None, nullable=True)
    playback_started_at: datetime | None = Field(None, nullable=True)
    current_device_id: str | None = Field(default=None, nullable=True)

    # Relations
    room: "Room" = Relationship(back_populates="session")
    queue_items: Mapped[list["QueueItem"]] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    queue_histories: Mapped[list["QueueHistory"]] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
