"""Session schemas for the API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.db.models.enum import ItemStatus, StreamingPlatforms


class CreateSession(BaseModel):
    """Schema for creating a new active session within a room.

    Attributes:
        room_id (UUID): The unique identifier of the room.
        current_platform (StreamingPlatforms): The streaming service being used.
    """

    room_id: UUID = Field(..., description="The UUID of the room to host this session.")
    current_platform: StreamingPlatforms = Field(
        ..., description="The streaming platform currently in use."
    )


class ReadSession(BaseModel):
    """Schema for the session data returned by the API.

    Attributes:
        id (UUID): The unique identifier of the session.
        room_id (UUID): The identifier of the room this session belongs to.
        current_platform (StreamingPlatforms): The streaming service currently active.
        current_song_id (str | None): The ID of the song currently playing.
        last_updated (datetime): The timestamp of the last session update.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="The unique identifier of the session.")
    room_id: UUID = Field(
        ..., description="The identifier of the room this session belongs to."
    )
    current_platform: StreamingPlatforms = Field(
        ..., description="The streaming platform currently in use."
    )
    current_song_id: str | None = Field(
        None, description="The ID of the song currently being played."
    )
    last_updated: datetime = Field(
        ..., description="The timestamp of the last recorded activity."
    )
    playback_status: ItemStatus | None = Field(
        None, description="The current playback status."
    )
    playback_position_ms: int | None = Field(
        None, description="The current playback position in milliseconds."
    )
    playback_started_at: datetime | None = Field(
        None, description="When the current track started playing."
    )
    current_device_id: str | None = Field(
        None, description="The device currently used for playback."
    )


class UpdateSession(BaseModel):
    """Schema for updating an existing session's state. All fields are optional.

    Attributes:
        current_song_id (str | None): The new song ID to be played.
        playback_status (ItemStatus | None): The current playback status.
        playback_position_ms (int | None): Current position in milliseconds.
        playback_started_at (datetime | None): When playback started.
        current_device_id (str | None): The device used for playback.
    """

    current_song_id: str | None = Field(
        None, description="The ID of the new song to play."
    )
    playback_status: ItemStatus | None = Field(
        None, description="The current playback status."
    )
    playback_position_ms: int | None = Field(
        None, description="The current playback position in milliseconds."
    )
    playback_started_at: datetime | None = Field(
        None, description="When the current track started playing."
    )
    current_device_id: str | None = Field(
        None, description="The device currently used for playback."
    )
