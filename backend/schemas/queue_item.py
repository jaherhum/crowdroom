from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateQueueItem(BaseModel):
    """
    Schema for validating the creation of a new queue item.

    Attributes:
        session_id: Unique identifier of the session.
        song_id: Unique identifier of the song to be added.
        added_by_user_id: ID of the user who added the song.
        position: Initial position in the queue.
    """
    session_id: UUID = Field(..., description="The active music session to which this queue item will belong.")
    song_id: UUID = Field(..., description="The identifier of the song to be added to the Spotify queue.")
    added_by_user_id: Optional[UUID] = Field(None, description="The ID of the user who added the song.")
    position: int = Field(..., ge=0, description="The position in the queue where the song should be placed.")


class ReadQueueItem(BaseModel):
    """
    Schema for the queue item data returned by the API.

    Attributes:
        id: Unique identifier of the queue item.
        session_id: Unique identifier of the session.
        song_id: Unique identifier of the queued song.
        added_by_user_id: ID of the user who added the song.
        position: Current position of the song in the queue.
        votes_skip: Current number of skip votes accumulated for the song.
    """
    id: UUID = Field(..., description="The unique identifier for this queue entry.")
    session_id: UUID = Field(..., description="The identifier of the session this queue item belongs to.")
    song_id: UUID = Field(..., description="The identifier of the song currently stored in the queue.")
    added_by_user_id: Optional[UUID] = Field(None, description="The ID of the user who added the song.")
    position: int = Field(..., ge=0, description="The current position of the song in the queue.")
    votes_skip: int = Field(..., ge=0, description="The current number of skip votes received by this queue item.")

    model_config = ConfigDict(from_attributes=True)


class MoveQueueItem(BaseModel):
    """
    Schema for moving a queue item to a new position.

    Attributes:
        new_position: New target position in the queue.
    """
    new_position: int = Field(..., ge=0, description="The new target position for the queue item.")