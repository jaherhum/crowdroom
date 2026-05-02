"""Schemas for managing skip votes on queue items."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateQueueVote(BaseModel):
    """Schema for casting a skip vote on the currently playing song.

    Each user can only vote once per queue item. When the total votes
    reach the room's skip_threshold (default 50% of members), the song
    is automatically skipped and moved to history.

    Attributes:
        queue_item_id: The queue item the user wants to skip.
        user_id: The user casting the vote.
    """

    queue_item_id: UUID = Field(
        ...,
        description="The unique identifier of the queue item to vote for skipping.",
    )
    user_id: UUID = Field(
        ...,
        description="The unique identifier of the user casting the skip vote.",
    )


class ReadQueueVote(BaseModel):
    """Schema for a skip vote returned by the API.

    Attributes:
        id: Unique identifier of this vote record.
        queue_item_id: The queue item that was voted on.
        user_id: The user who cast the vote.
        voted_at: Timestamp when the vote was cast.
    """

    id: UUID = Field(
        ...,
        description="The unique identifier of this vote record.",
    )
    queue_item_id: UUID = Field(
        ...,
        description="The unique identifier of the queue item that was voted on.",
    )
    user_id: UUID = Field(
        ...,
        description="The unique identifier of the user who cast this vote.",
    )
    voted_at: datetime = Field(
        ...,
        description="The timestamp when this skip vote was cast.",
    )

    model_config = ConfigDict(from_attributes=True)
