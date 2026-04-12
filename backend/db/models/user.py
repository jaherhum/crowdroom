from typing import Optional

from sqlmodel import SQLModel, Field, Relationship
from uuid import uuid4, UUID

class User(SQLModel, table=True):
    """
    Database model representing a User in the system.

    This model defines the persistent storage for user identities, supporting
    both authenticated users (with email/password) and anonymous/local users
    (without email/password).

    Attributes:
        id (UUID): Primary key, universally unique identifier.
        username (str): Unique handle for the user (max 32 chars).
        email (str, optional): Email address for authentication. Nullable for local/anonymous users.
        hashed_password (str, optional): Argon2/Bcrypt hashed password. Nullable for local/anonymous users.
        room (Optional[Room]): Relationship to the Room the user belongs to.
        queue_items (list[QueueItem]): List of items added to the queue by this user.
    """
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(default_factory=str, max_length=32, unique=True, nullable=False)
    email: Optional[str] = Field(default=None, max_length=255, unique=True, nullable=True)
    hashed_password: Optional[str] = Field(default=None, max_length=255, nullable=True)

    # Relations
    room: Optional["Room"] = Relationship(back_populates="user")
    queue_items: list["QueueItem"] = Relationship(back_populates="added_by")
