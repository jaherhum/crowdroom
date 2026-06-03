"""Service for managing the music queue."""

from uuid import UUID

from backend.api.websocket import manager
from backend.core.exceptions import EntityNotFoundException
from backend.db.models.queue_item import QueueItem
from backend.repositories.queue_repo import QueueRepository
from backend.repositories.session_repo import SessionRepository
from backend.schemas.queue_item import ReadQueueItemDetail
from backend.schemas.song import ReadSong


class QueueService:
    """Service for managing queue items within a session.

    Handles adding, removing, and retrieving queue items, as well as
    tracking the current playing song and queue statistics.
    """

    def __init__(
        self,
        queue_repo: QueueRepository,
        session_repo: SessionRepository | None = None,
    ) -> None:
        """Initialize the QueueService with its repository.

        Args:
            queue_repo: Repository for all queue data operations.
            session_repo: Repository for session lookups (needed for broadcasting).
        """
        self._queue_repo = queue_repo
        self._session_repo = session_repo

    async def add_to_queue(
        self,
        session_id: UUID,
        song_id: UUID,
        added_by_user_id: UUID | None = None,
        group: str = "manual",
    ) -> QueueItem:
        """Add a song to the end of a queue group.

        Delegates to atomic repository method to prevent TOCTOU race
        conditions between reading max position and inserting a new item.

        Args:
            session_id: The session whose queue to add to.
            song_id: The song to queue.
            added_by_user_id: The user who added the song (optional).
            group: The queue group ('manual' or 'playlist'). Defaults to 'manual'.

        Returns:
            QueueItem: The newly created queue item.
        """
        item = self._queue_repo.add_to_queue_atomic(
            session_id, song_id, added_by_user_id, group
        )
        await self._broadcast_queue_updated(session_id, action="added")
        if item.position == 0:
            await self._broadcast_song_changed(session_id, item.song)
        return item

    async def remove_from_queue(self, queue_item_id: UUID) -> None:
        """Remove a song from the queue.

        Args:
            queue_item_id: The queue item to remove.

        Raises:
            EntityNotFoundException: If the queue item does not exist.
        """
        item = self.get_queue_item(queue_item_id)
        session_id = item.session_id
        if not self._queue_repo.delete(queue_item_id):
            raise EntityNotFoundException("QueueItem", queue_item_id)
        await self._broadcast_queue_updated(session_id, action="removed")

    def get_queue_item(self, queue_item_id: UUID) -> QueueItem:
        """Retrieve a single queue item.

        Args:
            queue_item_id: The unique identifier of the queue item.

        Returns:
            QueueItem: The queue item.

        Raises:
            EntityNotFoundException: If the queue item is not found.
        """
        item = self._queue_repo.get_by_id(queue_item_id)
        if not item:
            raise EntityNotFoundException("QueueItem", queue_item_id)
        return item

    def get_queue(self, session_id: UUID) -> list[QueueItem]:
        """Retrieve the full queue for a session, ordered by position.

        Args:
            session_id: The session whose queue to retrieve.

        Returns:
            list[QueueItem]: The ordered list of queue items.
        """
        return self._queue_repo.get_all_by_session(session_id)

    def get_current_song(self, session_id: UUID) -> QueueItem | None:
        """Retrieve the song currently playing (position 0).

        Args:
            session_id: The session to check.

        Returns:
            QueueItem | None: The first item in the queue, or None if empty.
        """
        return self._queue_repo.get_first_item(session_id)

    def get_queue_count(self, session_id: UUID) -> int:
        """Get the total number of items in a queue.

        Args:
            session_id: The session to count items for.

        Returns:
            int: The number of items in the queue.
        """
        return self._queue_repo.count_by_session(session_id)

    async def broadcast_queue_reordered(self, session_id: UUID) -> None:
        """Broadcast a queue reorder event to room members.

        Args:
            session_id: The session whose queue was reordered.
        """
        await self._broadcast_queue_updated(session_id, action="reordered")

    async def _broadcast_queue_updated(self, session_id: UUID, action: str) -> None:
        """Broadcast current queue state to all room members via WebSocket.

        Args:
            session_id: The session whose queue changed.
            action: What triggered the update ('added', 'removed', 'reordered').
        """
        if not self._session_repo:
            return

        session_obj = self._session_repo.get_by_id(session_id)
        if not session_obj:
            return

        room_id = session_obj.room_id
        queue_items = self.get_queue(session_id)
        queue_payload = [
            ReadQueueItemDetail.model_validate(item).model_dump(mode="json")
            for item in queue_items
        ]

        await manager.broadcast(
            {
                "type": "queue_updated",
                "action": action,
                "room_id": str(room_id),
                "queue": queue_payload,
            },
            str(room_id),
        )

    async def _broadcast_song_changed(self, session_id: UUID, song) -> None:
        """Broadcast song_changed event when first song starts playing.

        Args:
            session_id: The session whose playback started.
            song: The song that is now playing.
        """
        if not self._session_repo:
            return

        session_obj = self._session_repo.get_by_id(session_id)
        if not session_obj:
            return

        room_id = session_obj.room_id
        song_payload = ReadSong.model_validate(song).model_dump(mode="json")

        await manager.broadcast(
            {
                "type": "song_changed",
                "room_id": str(room_id),
                "song": song_payload,
            },
            str(room_id),
        )
