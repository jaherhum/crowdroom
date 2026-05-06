"""Database model for playback history of queued songs."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.db.models.session import Session
    from backend.db.models.song import Song


class QueueHistory(SQLModel, table=True):
    """Database model tracking songs that have been played or skipped.

    Maintains a history of recently played songs per session, typically
    capped at 10-15 entries for cleanup and performance.

    Attributes:
        id (UUID): Primary key, unique identifier for the history entry.
        session_id (UUID): Foreign key referencing the session that played the song.
        song_id (UUID): Foreign key referencing the song that was played.
        played_at (datetime): Timestamp when the song was played or skipped.
        session (Session): Relationship back to the parent session.
        song (Song): Relationship back to the song metadata.
    """

    __tablename__ = "queue_histories"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="sessions.id", nullable=False)
    song_id: UUID = Field(foreign_key="songs.id", nullable=False)
    played_at: datetime = Field(default_factory=datetime.now, nullable=False)

    # Relations
    session: "Session" = Relationship(back_populates="queue_histories")
    song: "Song" = Relationship(back_populates="queue_histories")
