from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from backend.db.models.enum import PlaybackStatus, StreamingPlatforms


class Session(SQLModel, table=True):
    """Database model representing an active music playback session.

    A Session is tied to a Room and tracks the current state of playback,
    including the platform being used and the song currently playing.

    Attributes:
        id (UUID): Primary key, unique identifier for the session.
        room_id (UUID): Foreign key referencing the Room this session belongs to.
        current_platform (StreamingPlatforms): The streaming service currently in use.
        current_song_id (str, optional): The external ID of the song being played.
        playback_status (PlaybackStatus): The current state of playback (playing, paused, etc.).
        last_updated (datetime): Timestamp of the last session state update.
        room (Room): Relationship to the parent Room.
        queue_items (list[QueueItem]): List of items currently in the session's queue.
    """

    __tablename__ = "sessions"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    room_id: UUID = Field(foreign_key="rooms.id", nullable=False, unique=True)
    current_platform: StreamingPlatforms = Field(
        default=StreamingPlatforms.SPOTIFY, nullable=False
    )
    current_song_id: Optional[str] = Field(default=None, nullable=True)
    playback_status: PlaybackStatus = Field(
        default=PlaybackStatus.STOPPED, nullable=False
    )

    last_updated: datetime = Field(default_factory=datetime.now, nullable=False)

    # Relations
    room: "Room" = Relationship(back_populates="session")
    queue_items: list["QueueItem"] = Relationship(back_populates="session")
