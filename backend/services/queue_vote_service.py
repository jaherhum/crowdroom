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
        """Initialize the QueueVoteService with its dependencies.

        Args:
            queue_vote_repo: Repository for persisting and querying votes.
            playback_service: Optional PlaybackService for threshold-based skip.
        """
        self._repo = queue_vote_repo
        self._playback_service = playback_service

    def cast_vote(self, queue_item_id: UUID, user_id: UUID) -> QueueVote:
        """Cast a skip vote for a specific queue item.

        Rejects duplicate votes from the same user on the same queue item.
        If the total vote count reaches the room's skip threshold (via
        PlaybackService), triggers the finish_song flow to advance playback.

        Args:
            queue_item_id: UUID of the queue item to vote on.
            user_id: UUID of the user casting the vote.

        Returns:
            The newly saved QueueVote instance.

        Raises:
            EntityExistsException: If the user already voted on this item.
        """
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
        """Verify whether votes on a queue item meet the room's skip threshold.

        Looks up the room's configured skip_threshold setting and compares
        it against the current vote count. If the threshold is met or
        exceeded, triggers finish_song to advance playback.

        This is an internal method that safely returns without action if
        any part of the lookup chain (queue item, session, room, settings)
        is missing.

        Args:
            vote_obj: The QueueVote whose associated item's votes to evaluate.
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
        """Return the total number of skip votes for a queue item.

        Args:
            queue_item_id: UUID of the queue item to count votes for.

        Returns:
            The number of votes cast on this queue item.
        """
        return self._repo.count_by_item(queue_item_id)
