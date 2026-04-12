from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr

from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    """
    Database model representing a user.
    Supports both local (anonymous/temporary) and online (authenticated) users.
    """
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(default_factory=str, max_length=32, unique=True, nullable=False)
    email: Optional[str] = Field(default=None, max_length=255, unique=True, nullable=True)
    hashed_password: Optional[str] = Field(default=None, max_length=255, nullable=True)

    # Relations
    room: Optional["Room"] = Relationship(back_populates="user")
    queue_items: List["QueueItem"] = Relationship(back_populates="added_by")
