"""Database model representing a User in the system."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.db.models.queue_item import QueueItem
    from backend.db.models.room_member import RoomMember


class User(SQLModel, table=True):
    """Database model representing a User in the system.

    This model defines the persistent storage for user identities, supporting
    both authenticated users (with email/password) and anonymous/local users
    (without email/password).

    Attributes:
        id (UUID): Primary key, universally unique identifier.
        username (str): Unique handle for the user (max 32 chars).
        email (str, optional): Email address for authentication.
        hashed_password (str, optional): Argon2/Bcrypt hashed password.
        room_memberships (list[RoomMember]): List of rooms the user is a member of.
        queue_items (list[QueueItem]): List of items added to the queue.
    """

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(max_length=32, unique=True, nullable=False)
    email: Optional[str] = Field(
        default=None, max_length=255, unique=True, nullable=True
    )
    hashed_password: Optional[str] = Field(default=None, max_length=255, nullable=True)

    # Relations
    room_memberships: list["RoomMember"] = Relationship(back_populates="user")
    queue_items: list["QueueItem"] = Relationship(back_populates="added_by")
