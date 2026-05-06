"""Service for managing playback history."""

from uuid import UUID

from backend.db.models.queue_history import QueueHistory
from backend.repositories.queue_history_repo import QueueHistoryRepository

MAX_HISTORY = 15


class QueueHistoryService:
    """Service for managing playback history."""

    def __init__(self, queue_history_repo: QueueHistoryRepository) -> None:
        self._repo = queue_history_repo

    def add_to_history(self, session_id: UUID, song_id: UUID) -> QueueHistory:
        """Record a song as played. Auto-prunes old entries."""
        entry = QueueHistory(session_id=session_id, song_id=song_id)
        result = self._repo.create(entry)
        self._repo.delete_oldest(session_id, keep=MAX_HISTORY)
        return result

    def get_history(self, session_id: UUID, limit: int = 15) -> list[QueueHistory]:
        """Get playback history for a session, newest first."""
        return self._repo.get_all_by_session(session_id, limit=limit)
