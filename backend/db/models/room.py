from typing import Optional, Any, Dict
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship


class Room(SQLModel, table=True):
    """
    Database model representing a virtual meeting room.

    A Room acts as the primary container for music sessions and users. 
    It can be public or private and holds specific configuration settings.

    Attributes:
        id (UUID): Primary key, unique identifier for the room.
        host_user_id (UUID): Foreign key referencing the user who owns/created the room.
        room_name (str): Display name of the room.
        is_private (bool): Flag indicating if the room is private (hidden from public list).
        settings (dict): JSON-based dictionary for storing room-specific configurations.
        user (User): Relationship to the host user.
        session (Optional[Session]): Relationship to the current active session in this room.
    """
    __tablename__ = "rooms"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    host_user_id: UUID = Field(foreign_key="users.id", nullable=False)
    room_name: str = Field(default_factory=str, max_length=255, nullable=False)
    is_private: bool = Field(default=False, nullable=False)
    settings: Dict[str, Any] = Field(default_factory=dict, nullable=False, sa_column_kwargs={"type": "JSON"})

    # Relations
    user: "User" = Relationship(back_populates="room")
    session: Optional["Session"] = Relationship(back_populates="room")