"""Service for coordinating playback lifecycle across session and queue."""

from uuid import UUID

from backend.db.models.enum import PlaybackStatus
from backend.repositories.session_repo import SessionRepository
from backend.services.queue_history_service import QueueHistoryService
from backend.services.queue_service import QueueService


class PlaybackService:
    """Orchestrates playback transitions between session state and queue management.

    When a song finishes (natural end or skip), this service records it in history,
    removes it from the queue, and updates the session state to FINISHED.
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        queue_service: QueueService,
        queue_history_service: QueueHistoryService,
    ) -> None:
        self._session_repo = session_repo
        self._queue_service = queue_service
        self._queue_history_service = queue_history_service

    def finish_song(self, session_id: UUID) -> PlaybackStatus:
        """Advance to the next song after one finishes.

        Records the current song in history, removes it from the queue, and
        sets playback status to FINISHED.

        Returns:
            PlaybackStatus: The new session playback status (always FINISHED).
        """
        current_item = self._queue_service.get_current_song(session_id)
        if current_item is not None:
            self._queue_history_service.add_to_history(
                session_id=session_id, song_id=current_item.song_id
            )
            self._queue_service.remove_from_queue(current_item.id)

        self._session_repo.update(
            session_id, {"playback_status": PlaybackStatus.FINISHED}
        )

        return PlaybackStatus.FINISHED
