"""Schemas for playback lifecycle responses."""

from pydantic import BaseModel, Field


class FinishResponse(BaseModel):
    """Response schema when a song finishes and the queue advances.

    Attributes:
        status (PlaybackStatus): The new session playback status (STOPPED).
    """

    status: str = Field(
        ...,
        description="The updated playback status after finishing the current song.",
    )
