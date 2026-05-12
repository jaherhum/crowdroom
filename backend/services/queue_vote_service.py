"""Service for managing skip votes on queue items."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from backend.core.exceptions import EntityExistsException
from backend.db.models.queue_vote import QueueVote
from backend.repositories.queue_vote_repo import QueueVoteRepository
from backend.services.playback_service import PlaybackService


class QueueVoteService:
    """Service for managing skip votes."""

    def __init__(
        self,
        queue_vote_repo: QueueVoteRepository,
        playback_service: Optional[PlaybackService] = None,
    ) -> None:
        self._repo = queue_vote_repo
        self._playback_service = playback_service

    def cast_vote(self, queue_item_id: UUID, user_id: UUID) -> QueueVote:
        """Cast a skip vote. Raises if user already voted."""
        existing = self._repo.get_by_item_and_user(queue_item_id, user_id)
        if existing:
            raise EntityExistsException(
                f"QueueVote: User {user_id} already voted "
                f"on queue item {queue_item_id}",
            )
        vote = QueueVote(queue_item_id=queue_item_id, user_id=user_id)
        saved_vote = self._repo.create(vote)

        # Check threshold and trigger skip if met
        if self._playback_service:
            self._check_skip_threshold(saved_vote)

        return saved_vote

    def _check_skip_threshold(self, vote_obj: QueueVote) -> None:
        """Check if votes meet the room's skip threshold.

        If so, trigger finish_song to record history and advance queue.
        """
        queue_item = vote_obj.queue_item
        session_obj = queue_item.session
        if not session_obj:
            return

        room_obj = session_obj.room
        threshold = 1
        if room_obj and room_obj.settings:
            threshold = room_obj.settings.get("skip_threshold", 1)

        current_votes = self._repo.count_by_item(vote_obj.queue_item_id)
        if current_votes >= threshold:
            self._playback_service.finish_song(session_obj.id)

    def vote_count(self, queue_item_id: UUID) -> int:
        """Get the number of votes for a queue item."""
        return self._repo.count_by_item(queue_item_id)
