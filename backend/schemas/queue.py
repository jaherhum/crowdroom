from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateQueueItem(BaseModel):
    """
    Schema for validating the creation of a new queue item.

    Attributes:
        session_id (UUID): The unique identifier of the session.
        song_id (UUID): The unique identifier of the song to be added.
        added_by_user_id (Optional[UUID]): The ID of the user who added the song.
        position (int): The initial position in the queue.
        votes_skip (int): The initial number of skip votes.
    """
    session_id: UUID = Field(..., description="The active music session to which this item will belong.")
    song_id: UUID = Field(..., description="The identifier of the song to be added to the queue.")
    added_by_user_id: Optional[UUID] = Field(None, description="The ID of the user who added the song (optional).")
    position: int = Field(..., ge=0, description="The specific index in the queue where the song should be placed.")
    votes_skip: int = Field(..., ge=0, description="The initial count of skip votes.")

class ReadQueueItem(BaseModel):
    """
    Schema for the queue item data returned by the API.

    Attributes:
        id (UUID): The unique identifier of the queue item.
        session_id (UUID): The unique identifier of the session.
        song_id (UUID): The unique identifier of the song.
        added_by_user_id (Optional[UUID]): The ID of the user who added the song.
        position (int): The current position in the queue.
        votes_skip (int): The current number of skip votes.
    """
    id: UUID = Field(..., description="The unique identifier for this specific queue entry.")
    session_id: UUID = Field(..., description="The identifier of the session this item belongs to.")
    song_id: UUID = Field(..., description="The identifier of the song in this entry.")
    added_by_user_id: Optional[UUID] = Field(None, description="The ID of the user who added the song.")
    position: int = Field(..., description="The current position of the song in the queue.")
    votes_skip: int = Field(..., ge=0, description="The current number of skip votes accumulated.")

class MoveQueueItem(BaseModel):
    """
    Schema for the command to move a queue item to a new position.

    Attributes:
        new_position (int): The target index in the queue.
    """
    new_position: int = Field(..., ge=0, description="The target index in the queue for this item.")