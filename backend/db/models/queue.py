from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class QueueStatus(str, Enum):
    """Queue item status."""
    PENDING = "pending"
    PLAYING = "playing"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    REMOVED = "removed"


class QueueItemBase(SQLModel):
    """Base queue item schema."""
    song_id: int = Field(..., foreign_key="songs.id")
    room_id: int = Field(..., foreign_key="rooms.id")
    position: Optional[int] = Field(default=None, ge=0)
    status: QueueStatus = Field(default=QueueStatus.PENDING)


class QueueItemCreate(QueueItemBase):
    """Queue item creation schema."""
    user_id: int = Field(..., foreign_key="users.id")


class QueueItemUpdate(SQLModel):
    """Queue item update schema."""
    position: Optional[int] = Field(default=None, ge=0)
    status: Optional[QueueStatus] = Field(default=None)


class QueueItem(QueueItemBase, table=True):
    """Queue item database model."""
    __tablename__ = "queue_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(..., foreign_key="users.id")  # who added it
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Index for efficient room + status queries
    __table_args__ = ({"sqlite_autoincrement": True},)
