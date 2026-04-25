"""Room schemas for the API."""
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WelcomeMessage(BaseModel):
    """Represents the configuration for a room's welcome message.

    Attributes:
        title (str): The headline text shown to users.
        description (Optional[str]): A longer text providing more context.
    """

    title: str = Field(..., description="Title of the welcome message.", max_length=50)
    description: Optional[str] = Field(
        None, description="Set a description for the welcome message.", max_length=100
    )


class CreateRoom(BaseModel):
    """Schema for creating a new room.

    Attributes:
        host_user_id (UUID): The unique identifier of the user creating the room.
        room_name (str): The display name of the room.
        is_private (bool): Whether the room is hidden from public lists.
    """

    host_user_id: UUID = Field(..., description="Host's user ID.")
    room_name: str = Field(..., description="Room's name.", max_length=255)
    is_private: bool = Field(
        default=False, description="Whether if the room is private or public."
    )


class ReadRoom(BaseModel):
    """Schema for the room data returned by the API.

    Attributes:
        id (UUID): The unique identifier of the room.
        host_user_id (UUID): The UUID of the host user.
        room_name (str): The display name of the room.
        is_private (bool): Privacy status of the room.
        settings (Dict[str, Any]): The current configuration settings of the room.
    """

    id: UUID = Field(..., description="Room's ID.")
    host_user_id: UUID = Field(..., description="Host's user ID.")
    room_name: str = Field(..., description="Room's name.")
    is_private: bool = Field(
        ..., description="Whether if the room is private or public."
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Room configuration settings."
    )


class UpdateRoom(BaseModel):
    """Schema for updating an existing room. All fields are optional.

    Attributes:
        room_name (Optional[str]): The new name for the room.
        is_private (Optional[bool]): The new privacy status for the room.
        settings (Optional[Dict[str, Any]]): The new settings for the room.
    """

    room_name: Optional[str] = Field(None, description="Room's name.", max_length=255)
    is_private: Optional[bool] = Field(
        None, description="Whether if the room is private or public."
    )
    settings: Optional[Dict[str, Any]] = Field(
        None, description="Room's configuration settings."
    )


class RoomStateUpdate(BaseModel):
    """Schema for real-time room state updates."""

    type: str = Field(
        ...,
        description=(
            "The type of update (e.g., 'member_joined', 'member_left', "
            "'settings_updated')."
        ),
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="The data associated with the update."
    )
