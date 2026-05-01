"""Service for managing the music queue."""
from uuid import UUID

from backend.core.exceptions import EntityNotFoundException
from backend.db.models.queue_item import QueueItem
from backend.repositories.queue_repo import QueueRepository


class QueueService:
    """Service for managing queue items within a session.

    Handles adding, removing, and retrieving queue items, as well as
    tracking the current playing song and queue statistics.
    """

    def __init__(self, queue_repo: QueueRepository) -> None:
        self._queue_repo = queue_repo

    def add_to_queue(
        self, session_id: UUID, song_id: UUID, added_by_user_id: UUID | None = None
    ) -> QueueItem:
        """Add a song to the end of the queue.

        Args:
            session_id: The session whose queue to add to.
            song_id: The song to queue.
            added_by_user_id: The user who added the song (optional).

        Returns:
            QueueItem: The newly created queue item.
        """
        max_pos = self._queue_repo.get_max_position(session_id)
        queue_item = QueueItem(
            session_id=session_id,
            song_id=song_id,
            added_by_user_id=added_by_user_id,
            position=max_pos + 1,
        )
        return self._queue_repo.create(queue_item)

    def remove_from_queue(self, queue_item_id: UUID) -> None:
        """Remove a song from the queue.

        Args:
            queue_item_id: The queue item to remove.

        Raises:
            EntityNotFoundException: If the queue item does not exist.
        """
        self.get_queue_item(queue_item_id)
        self._queue_repo.delete(queue_item_id)

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
