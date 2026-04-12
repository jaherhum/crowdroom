from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from db.models import room

class WelcomeMessage(BaseModel):
    """
    Represents the configuration for a room's welcome message.

    Attributes:
        title (str): The headline text shown to users.
        description (Optional[str]): A longer text providing more context.
    """
    title: str = Field(..., description="Title of the welcome message.", max_length=50)
    description: Optional[str] = Field(None, description="Set a description for the welcome message.", max_length=100)

class CreateRoom(BaseModel):
    """
    Schema for creating a new room.

    Attributes:
        host_user_id (UUID): The unique identifier of the user creating the room.
        room_name (str): The display name of the room.
        is_private (bool): Whether the room is hidden from public lists.
    """
    host_user_id: UUID = Field(..., description="Host's user ID.")
    room_name: str = Field(..., description="Room's name.", max_length=50)
    is_private: bool = Field(..., description="Whether if the room is private or public.")

class ReadRoom(BaseModel):
    """
    Schema for the room data returned by the API.

    Attributes:
        host_user_id (UUID): The UUID of the host user.
        room_name (str): The display name of the room.
        is_private (bool): Privacy status of the room.
        settings (RoomSettings): The current configuration settings of the room.
    """
    host_user_id: UUID = Field(..., description="Host's user ID.")
    room_name: str = Field(..., description="Room's name.")
    is_private: bool = Field(..., description="Whether if the room is private or public.")

class UpdateRoom(BaseModel):
    """
    Schema for updating an existing room. All fields are optional.

    Attributes:
        room_name (Optional[str]): The new name for the room.
        is_private (Optional[bool]): The new privacy status for the room.
    """
    room_name: Optional[str] = Field(None, description="Room's name.", max_length=50)
    is_private: Optional[bool] = Field(None, description="Whether if the room is private or public.")

class SettingsRoom(BaseModel):
    """
    Represents the configuration settings for a specific room.

    Attributes:
        max_users (int): The maximum number of users allowed in the room.
        allow_voteskip (bool): Whether users can vote to skip the current song.
        welcome_message (Optional[WelcomeMessage]): An optional welcome message object.
    """
    max_users: int = Field(..., ge=1, le=500, description="Max number of users.")
    allow_voteskip: bool = Field(..., description="Allow vote skip votes.")
    welcome_message: Optional[WelcomeMessage] = Field(None, description="Adds a welcome message.")