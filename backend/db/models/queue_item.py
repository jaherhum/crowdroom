"""Database model for items in a music queue."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.db.models.queue_vote import QueueVote
    from backend.db.models.session import Session
    from backend.db.models.song import Song
    from backend.db.models.user import User


class QueueItem(SQLModel, table=True):
    """Database model representing an individual item in a music queue.

    This model links a specific song to a session and tracks its position,
    voting (skips), and the user who added it.

    Attributes:
        id (UUID): Primary key, unique identifier for the queue entry.
        session_id (UUID): Foreign key referencing the session this item belongs to.
        song_id (UUID): Foreign key referencing the song being queued.
        added_by_user_id (UUID, optional): ID of the user who added this item.
            Can be null if added by an external platform/system.
        position (int): The current order of the item in the queue.
        votes_skip (int): Counter for skip votes received for this item.
        song (Song): Relationship back to the song metadata.
        session (Session): Relationship back to the parent session.
        added_by (Optional[User]): Relationship to the user who added the item.
        queue_votes (list[QueueVote]): List of skip votes on this item.
    """
    __tablename__ = "queue_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key='sessions.id', nullable=False)
    song_id: UUID = Field(foreign_key='songs.id', nullable=False)
    added_by_user_id: Optional[UUID] = Field(
        default=None, foreign_key='users.id', nullable=True
    )

    position: int = Field(default=0, nullable=False)
    votes_skip: int = Field(default=0, nullable=False)
    group: str = Field(default="playlist", nullable=False, description="Queue group: 'manual' or 'playlist'")

    # Relations
    song: "Song" = Relationship(back_populates="queue_items")
    session: "Session" = Relationship(back_populates="queue_items")
    added_by: Optional["User"] = Relationship(back_populates="queue_items")
    queue_votes: Mapped[list["QueueVote"]] = Relationship(back_populates="queue_item")
