"""WebSocket event schemas for real-time broadcasting."""

from uuid import UUID

from pydantic import BaseModel

from backend.schemas.queue_item import ReadQueueItem
from backend.schemas.song import ReadSong


class QueueUpdatedEvent(BaseModel):
    """Payload for queue_updated WebSocket events.

    Attributes:
        type: Event type identifier, always 'queue_updated'.
        action: What triggered the update ('added', 'removed', 'reordered').
        room_id: The room whose queue changed.
        queue: Current full queue state after the change.
    """

    type: str = "queue_updated"
    action: str
    room_id: UUID
    queue: list[ReadQueueItem]


class SongChangedEvent(BaseModel):
    """Payload for song_changed WebSocket events.

    Attributes:
        type: Event type identifier, always 'song_changed'.
        room_id: The room where playback changed.
        song: Metadata of the now-playing song.
    """

    type: str = "song_changed"
    room_id: UUID
    song: ReadSong | None


class SkipVoteEvent(BaseModel):
    """Payload for skip_vote WebSocket events.

    Attributes:
        type: Event type identifier, always 'skip_vote'.
        room_id: The room where the vote was cast.
        queue_item_id: The queue item being voted on.
        voter_id: The user who cast the vote.
        current_votes: Total votes on this item after this vote.
        threshold: Number of votes required to trigger a skip.
        skip_triggered: Whether the skip threshold was reached.
    """

    type: str = "skip_vote"
    room_id: UUID
    queue_item_id: UUID
    voter_id: UUID
    current_votes: int
    threshold: int
    skip_triggered: bool


class PlaybackStateChangedEvent(BaseModel):
    """Payload for playback_state_changed WebSocket events.

    Attributes:
        type: Event type identifier, always 'playback_state_changed'.
        room_id: The room whose playback state changed.
        status: New playback status ('playing', 'paused', 'skipped', or 'stopped').
        track_id: Spotify track ID currently playing, if any.
    """

    type: str = "playback_state_changed"
    room_id: UUID
    status: str
    track_id: str | None = None
