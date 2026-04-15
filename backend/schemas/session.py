from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from db.models.enum import StreamingPlatforms, PlaybackStatus


class CreateSession(BaseModel):
    """
    Schema for creating a new active session within a room.

    Attributes:
        room_id (UUID): The unique identifier of the room where the session starts.
        current_platform (StreamingPlatforms): The streaming service being used (e.g., Spotify, YouTube).
        playback_status (PlaybackStatus): The initial playback state (e.g., paused, playing).
    """

    room_id: UUID = Field(..., description="The UUID of the room to host this session.")
    current_platform: StreamingPlatforms = Field(
        ..., description="The streaming platform currently in use."
    )
    playback_status: PlaybackStatus = Field(
        ..., description="The initial playback status of the session."
    )


class ReadSession(BaseModel):
    """
    Schema for the session data returned by the API.

    Attributes:
        id (UUID): The unique identifier of the session.
        room_id (UUID): The identifier of the room this session belongs to.
        current_platform (StreamingPlatforms): The streaming service currently active.
        current_song_id (Optional[str]): The ID of the song currently playing, if any.
        playback_status (PlaybackStatus): The current state of playback.
        last_updated (datetime): The timestamp of the last session update.
    """

    id: UUID = Field(..., description="The unique identifier of the session.")
    room_id: UUID = Field(
        ..., description="The identifier of the room this session belongs to."
    )
    current_platform: StreamingPlatforms = Field(
        ..., description="The streaming platform currently in use."
    )
    current_song_id: Optional[str] = Field(
        None, description="The ID of the song currently being played."
    )
    playback_status: PlaybackStatus = Field(
        ..., description="The current playback status."
    )
    last_updated: datetime = Field(
        ..., description="The timestamp of the last recorded activity in this session."
    )


class UpdateSession(BaseModel):
    """
    Schema for updating an existing session's state. All fields are optional.

    Attributes:
        current_song_id (Optional[str]): The new song ID to be played.
        playback_status (Optional[PlaybackStatus]): The new playback status (e.g., play, pause, stop).
    """

    current_song_id: Optional[str] = Field(
        None, description="The ID of the new song to play."
    )
    playback_status: Optional[PlaybackStatus] = Field(
        None, description="The updated playback status."
    )
