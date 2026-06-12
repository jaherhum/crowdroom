"""Room schemas for the API."""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WelcomeMessage(BaseModel):
    """Represents the configuration for a room's welcome message.

    Attributes:
        title (str): The headline text shown to users.
        description (Optional[str]): A longer text providing more context.
    """

    title: str = Field(..., description="Title of the welcome message.", max_length=50)
    description: str | None = Field(
        None, description="Set a description for the welcome message.", max_length=100
    )


class RoomSettings(BaseModel):
    """Room configuration settings."""

    skip_threshold: int = Field(default=2, ge=1, le=50, description="Skip threshold.")
    max_members: int = Field(
        default=50, ge=2, le=200, description="Maximum number of members allowed."
    )


class CreateRoom(BaseModel):
    """Schema for creating a new room.

    Attributes:
        host_user_id (UUID | None): Set by the server from JWT.
        room_name (str): The display name of the room.
        is_private (bool): Whether the room is hidden from public lists.
    """

    host_user_id: UUID | None = Field(
        None, description="Host's user ID (set by server from JWT)."
    )
    room_name: str = Field(..., description="Room's name.", max_length=255)
    is_private: bool = Field(
        default=False, description="Whether if the room is private or public."
    )
    pin: str | None = Field(None, description="Pin of the room.")
    is_visible: bool = Field(True, description="Whether if the room is visible.")
    settings: RoomSettings = Field(
        default_factory=RoomSettings,
        description="Room configuration settings.",
    )

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str | None) -> str | None:
        """Validate PIN format: must be 4-6 digits if provided."""
        if value is None:
            return value
        if not re.match(r"^\d{4,6}$", value):
            raise ValueError("PIN must be 4-6 digits.")
        return value

    @model_validator(mode="after")
    def validate_model(self):
        """Enforce PIN/privacy consistency rules."""
        if self.is_private is True and self.pin is None:
            raise ValueError("A private room needs a PIN.")
        elif self.is_private is False and self.pin is not None:
            raise ValueError("A public room can't have a PIN.")
        return self


class ReadRoom(BaseModel):
    """Schema for the room data returned by the API.

    Attributes:
        id (UUID): The unique identifier of the room.
        host_user_id (UUID): The UUID of the host user.
        room_name (str): The display name of the room.
        is_private (bool): Privacy status of the room.
        settings (Dict[str, Any]): The current configuration settings of the room.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Room's ID.")
    host_user_id: UUID = Field(..., description="Host's user ID.")
    room_name: str = Field(..., description="Room's name.")
    is_private: bool = Field(
        ..., description="Whether if the room is private or public."
    )
    is_visible: bool = Field(..., description="Whether if the room is visible or not.")
    room_code: str = Field(..., description="Room's code.")
    settings: RoomSettings = Field(
        default_factory=RoomSettings, description="Room configuration settings."
    )


class UpdateRoom(BaseModel):
    """Schema for updating an existing room. All fields are optional.

    Attributes:
        room_name (Optional[str]): The new name for the room.
        is_private (Optional[bool]): The new privacy status for the room.
        settings (Optional[Dict[str, Any]]): The new settings for the room.
    """

    room_name: str | None = Field(None, description="Room's name.", max_length=255)
    is_private: bool | None = Field(
        None, description="Whether if the room is private or public."
    )
    pin: str | None = Field(None, description="Pin of the room.")
    is_visible: bool | None = Field(
        None, description="Whether if the room is visible or not."
    )
    settings: RoomSettings | None = Field(
        None, description="Room's configuration settings."
    )

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str | None) -> str | None:
        """Validate PIN format: must be 4-6 digits if provided."""
        if value is None:
            return value
        if not re.match(r"^\d{4,6}$", value):
            raise ValueError("PIN must be 4-6 digits.")
        return value


class RoomStateUpdate(BaseModel):
    """Schema for real-time room state updates."""

    type: str = Field(
        ...,
        description=(
            "The type of update (e.g., 'member_joined', 'member_left', "
            "'settings_updated')."
        ),
    )
    payload: dict[str, Any] = Field(
        ..., description="The data associated with the update."
    )


class JoinRoom(BaseModel):
    """Request body for joining a room."""

    pin: str | None = Field(None, description="Pin of the room.")
    invite_token: str | None = Field(None, description="Invite token for the room.")


class BannedUserRead(BaseModel):
    """A banned user as shown to the host in the ban-management panel."""

    user_id: UUID = Field(..., description="The banned user's ID.")
    username: str = Field(..., description="The banned user's username.")
    banned_at: datetime = Field(..., description="When the ban was issued.")
