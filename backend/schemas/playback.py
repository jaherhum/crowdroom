"""Schemas for playback lifecycle responses."""

from uuid import UUID

from pydantic import BaseModel, Field


class FinishResponse(BaseModel):
    """Response schema when a song finishes and the queue advances.

    Attributes:
        status (str): The updated item status after finishing the current song.
    """

    status: str = Field(
        ...,
        description="The updated playback status after finishing the current song.",
    )


class PlayRequest(BaseModel):
    """Request body for starting playback of a specific song.

    Attributes:
        song_id: Internal UUID of the song to play.
        device_id: Optional Spotify device ID to target.
    """

    song_id: UUID | None = Field(
        None, description="Internal song UUID to play. Omit to resume current."
    )
    device_id: str | None = Field(
        None, description="Spotify device ID. Uses active device if omitted."
    )


class PlaybackStateResponse(BaseModel):
    """Response schema for current playback state.

    Attributes:
        is_playing: Whether audio is currently playing.
        track_id: Spotify track ID of the current song.
        progress_ms: Current playback position in milliseconds.
        device_id: Active device ID.
    """

    is_playing: bool = Field(..., description="Whether audio is currently playing.")
    track_id: str | None = Field(None, description="Spotify track ID.")
    progress_ms: int | None = Field(None, description="Playback position in ms.")
    device_id: str | None = Field(None, description="Active Spotify device ID.")
