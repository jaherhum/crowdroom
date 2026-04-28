"""Database model for skip votes on queue items."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from backend.db.models.queue_item import QueueItem
    from backend.db.models.user import User


class QueueVote(SQLModel, table=True):
    """Database model representing a skip vote by a user on a queue item.

    Each user can only vote once per queue item. When the total votes reach
    50% of the room members, the song is skipped and moved to history.

    Attributes:
        id (UUID): Primary key, unique identifier for the vote.
        queue_item_id (UUID): Foreign key referencing the queued song being voted on.
        user_id (UUID): Foreign key referencing the user who cast the vote.
        voted_at (datetime): Timestamp when the vote was cast.
        queue_item (QueueItem): Relationship back to the queue item.
        user (User): Relationship back to the voter.
    """

    __tablename__ = "queue_votes"
    __table_args__ = (
        UniqueConstraint("queue_item_id", "user_id", name="uq_queue_item_user_vote"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    queue_item_id: UUID = Field(foreign_key="queue_items.id", nullable=False)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    voted_at: datetime = Field(default_factory=datetime.now, nullable=False)

    # Relations
    queue_item: "QueueItem" = Relationship(back_populates="queue_votes")
    user: "User" = Relationship(back_populates="user_votes")
