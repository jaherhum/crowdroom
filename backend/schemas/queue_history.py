"""Schemas for managing playback history of queued songs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateQueueHistory(BaseModel):
    """Schema for creating a new playback history entry.

    History entries are created internally by the service when a song
    finishes playing or is skipped. This schema is used by the service
    layer to instantiate the model.

    Attributes:
        session_id: The session where the song was played.
        song_id: The song that was played.
    """

    session_id: UUID = Field(
        ...,
        description="The unique identifier of the session where the song was played.",
    )
    song_id: UUID = Field(
        ..., description="The unique identifier of the song that was played."
    )


class HistorySong(BaseModel):
    """Inline song data for history entries."""

    title: str
    artist: str
    album_art_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReadQueueHistory(BaseModel):
    """Schema for a playback history entry returned by the API.

    Attributes:
        id: Unique identifier of this history entry.
        session_id: The session where the song was played.
        song_id: The song that was played.
        played_at: Timestamp when the song was played or skipped.
        song: Nested song metadata.
    """

    id: UUID = Field(..., description="The unique identifier of this history entry.")
    session_id: UUID = Field(
        ...,
        description="The unique identifier of the session where the song was played.",
    )
    song_id: UUID = Field(
        ..., description="The unique identifier of the song that was played."
    )
    played_at: datetime = Field(
        ..., description="The timestamp when the song was played or skipped."
    )
    song: HistorySong | None = None

    model_config = ConfigDict(from_attributes=True)
