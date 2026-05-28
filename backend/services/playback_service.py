"""Service for coordinating playback lifecycle across session and queue."""

from uuid import UUID

from backend.api.websocket import manager
from backend.db.models.enum import ItemStatus
from backend.db.models.queue_history import QueueHistory
from backend.db.models.song import Song
from backend.repositories.queue_history_repo import QueueHistoryRepository
from backend.repositories.session_repo import SessionRepository
from backend.schemas.song import ReadSong
from backend.services.queue_service import QueueService

MAX_HISTORY = 15


class PlaybackService:
    """Orchestrates playback transitions between queue item states and history.

    When a song finishes (natural end or skip), this service records it in history,
    removes it from the queue, and updates the queue item state.
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        queue_service: QueueService,
        queue_history_repo: QueueHistoryRepository,
    ) -> None:
        """Initialize the PlaybackService with its dependencies.

        Args:
            session_repo: Repository for updating playback state.
            queue_service: Service for retrieving and removing queue items.
            queue_history_repo: Repository for recording finished songs.
        """
        self._session_repo = session_repo
        self._queue_service = queue_service
        self._queue_history_repo = queue_history_repo

    async def finish_song(self, session_id: UUID) -> str:
        """Advance to the next song after one finishes.

        Records the current song in history, updates its status to FINISHED,
        and removes it from the queue.

        Args:
            session_id: The session whose playback is finishing.

        Returns:
            str: "finished" to indicate the operation completed.
        """
        current_item = self._queue_service.get_current_song(session_id)
        if current_item is not None:
            current_item.playback_status = ItemStatus.FINISHED
            self._session_repo.update(current_item.session_id, {})

            self._record_history(session_id, current_item.song_id)
            await self._queue_service.remove_from_queue(current_item.id)

            next_item = self._queue_service.get_current_song(session_id)
            next_song = next_item.song if next_item else None
            await self._broadcast_song_changed(session_id, next_song)

        return "finished"

    def _record_history(self, session_id: UUID, song_id: UUID) -> None:
        """Persist a finished song to playback history and enforce size limit.

        Creates a new QueueHistory entry and prunes the oldest records if
        the total exceeds MAX_HISTORY (15 entries).

        Args:
            session_id: The session in which the song was played.
            song_id: The song that was just finished.
        """
        entry = QueueHistory(session_id=session_id, song_id=song_id)
        self._queue_history_repo.create(entry)
        self._queue_history_repo.delete_oldest(session_id, keep=MAX_HISTORY)

    async def _broadcast_song_changed(
        self, session_id: UUID, song: Song | None
    ) -> None:
        """Broadcast song_changed event to all room members via WebSocket.

        Args:
            session_id: The session whose playback changed.
            song: The new now-playing song, or None if queue is empty.
        """
        session_obj = self._session_repo.get_by_id(session_id)
        if not session_obj:
            return
        room_id = session_obj.room_id
        if song is None:
            song_payload = None
        else:
            song_payload = ReadSong.model_validate(song).model_dump(mode="json")

        await manager.broadcast(
            {
                "type": "song_changed",
                "room_id": str(room_id),
                "song": song_payload,
            },
            str(room_id),
        )
