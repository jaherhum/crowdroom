"""Database model representing a User in the system."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.db.models.platform_connection import PlatformConnection
    from backend.db.models.queue_item import QueueItem
    from backend.db.models.queue_vote import QueueVote
    from backend.db.models.room import Room


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
        room_id (Optional[UUID]): Foreign key to the room the user is currently in.
        room (Optional[Room]): Relationship to the Room the user belongs to.
        queue_items (list[QueueItem]): List of items added to the queue.
        user_votes (list[QueueVote]): List of skip votes cast by this user.
    """

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(max_length=32, unique=True, nullable=False)
    email: str | None = Field(default=None, max_length=255, unique=True, nullable=True)
    hashed_password: str | None = Field(default=None, max_length=255, nullable=True)
    avatar_path: str | None = Field(default=None, max_length=255, nullable=True)
    room_id: UUID | None = Field(default=None, foreign_key="rooms.id", nullable=True)
    token_version: int = Field(default=0, nullable=False)

    # Relations
    room: "Room" = Relationship(
        back_populates="users",
        sa_relationship_kwargs={"foreign_keys": "[User.room_id]"},
    )
    queue_items: Mapped[list["QueueItem"]] = Relationship(back_populates="added_by")
    user_votes: Mapped[list["QueueVote"]] = Relationship(back_populates="user")
    platform_connections: Mapped[list["PlatformConnection"]] = Relationship(
        back_populates="user"
    )
