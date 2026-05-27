"""WebSocket event schemas for real-time broadcasting."""

from uuid import UUID

from pydantic import BaseModel

from backend.schemas.queue_item import ReadQueueItem


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
