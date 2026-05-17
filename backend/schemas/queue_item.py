"""Queue item schemas for the API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateQueueItem(BaseModel):
    """Schema for validating the creation of a new queue item.

    Position is auto-calculated by the service (appends to end of the group).

    Attributes:
        session_id (UUID): Unique identifier of the session.
        song_id (UUID): Unique identifier of the song to be added.
        group (str): Queue group ('manual' or 'playlist'). Defaults to 'manual'.
    """

    session_id: UUID = Field(
        ..., description="The active music session to which this item belongs."
    )
    song_id: UUID = Field(
        ..., description="The identifier of the song to be added to the queue."
    )
    group: str = Field(
        default="manual", description="Queue group: 'manual' or 'playlist'."
    )


class ReadQueueItem(BaseModel):
    """Schema for the queue item data returned by the API.

    Attributes:
        id (UUID): Unique identifier of the queue item.
        session_id (UUID): Unique identifier of the session.
        song_id (UUID): Unique identifier of the queued song.
        added_by_user_id (Optional[UUID]): ID of the user who added the song.
        position (int): Current position of the song in the queue.
        votes_skip (int): Current number of skip votes accumulated for the song.
    """

    id: UUID = Field(..., description="The unique identifier for this queue entry.")
    session_id: UUID = Field(
        ..., description="The identifier of the session this item belongs to."
    )
    song_id: UUID = Field(
        ..., description="The identifier of the song currently in the queue."
    )
    added_by_user_id: UUID | None = Field(
        None, description="The ID of the user who added the song."
    )
    position: int = Field(
        ..., ge=0, description="The current position of the song in the queue."
    )
    votes_skip: int = Field(
        ..., ge=0, description="The current number of skip votes received."
    )

    model_config = ConfigDict(from_attributes=True)
