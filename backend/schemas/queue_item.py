"""Queue item schemas for the API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.db.models.enum import StreamingPlatforms


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


class QueueItemSong(BaseModel):
    """Inline song data within a queue item detail response.

    Attributes:
        id (UUID): Internal song identifier.
        external_id (str): Platform-specific track ID.
        title (str): Song title.
        artist (str): Artist name.
        platform (StreamingPlatforms): Streaming service of origin.
        duration (float): Duration in seconds.
        album_art_url (str | None): Cover art URL.
    """

    id: UUID
    external_id: str
    title: str
    artist: str
    platform: StreamingPlatforms
    duration: float
    album_art_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class QueueItemUser(BaseModel):
    """Inline user data within a queue item detail response.

    Attributes:
        id (UUID): User identifier.
        username (str): Display name.
    """

    id: UUID
    username: str

    model_config = ConfigDict(from_attributes=True)


class ReadQueueItemDetail(BaseModel):
    """Queue item with nested song and user data for frontend display.

    Attributes:
        id (UUID): Queue item identifier.
        session_id (UUID): Session this item belongs to.
        position (int): Queue position.
        votes_skip (int): Skip vote count.
        song (QueueItemSong): Full song metadata.
        added_by (QueueItemUser | None): User who added the item.
    """

    id: UUID
    session_id: UUID
    position: int = Field(..., ge=0)
    votes_skip: int = Field(..., ge=0)
    song: QueueItemSong
    added_by: QueueItemUser | None = None

    model_config = ConfigDict(from_attributes=True)
