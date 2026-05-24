"""Database model representing a user's connection to a streaming platform."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from backend.db.models.enum import StreamingPlatforms

if TYPE_CHECKING:
    from backend.db.models.user import User


class PlatformConnection(SQLModel, table=True):
    """Database model representing a user's connection to a streaming platform.

    Stores encrypted platform-specific credentials (e.g., client_id + client_secret
    for Spotify, API key for YouTube). One connection per platform per user.

    Attributes:
        id: Primary key, unique identifier.
        user_id: Foreign key referencing the owning user.
        platform: The streaming service this connection is for.
        credentials_encrypted: Fernet-encrypted JSON string of platform credentials.
        user: Relationship to the owning User.
    """

    __tablename__ = "platform_connections"
    __table_args__ = (UniqueConstraint("user_id", "platform", name="uq_user_platform"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    platform: StreamingPlatforms = Field(nullable=False)
    credentials_encrypted: str = Field(nullable=False)

    # Relations
    user: "User" = Relationship(back_populates="platform_connections")
