"""Service for managing skip votes on queue items."""

from __future__ import annotations

import time
from uuid import UUID

from backend.api.websocket import manager
from backend.core.config import settings
from backend.core.exceptions import (
    EntityExistsException,
    EntityNotFoundException,
    TooManyRequestsException,
)
from backend.db.models.queue_vote import QueueVote
from backend.repositories.queue_vote_repo import QueueVoteRepository
from backend.services.playback_service import PlaybackService

_vote_cooldowns: dict[UUID, float] = {}


class QueueVoteService:
    """Service for managing skip votes."""

    def __init__(
        self,
        queue_vote_repo: QueueVoteRepository,
        playback_service: PlaybackService | None = None,
    ) -> None:
        """Initialize the QueueVoteService with its dependencies.

        Args:
            queue_vote_repo: Repository for persisting and querying votes.
            playback_service: Optional PlaybackService for threshold-based skip.
        """
        self._repo = queue_vote_repo
        self._playback_service = playback_service

    def _check_cooldown(self, user_id: UUID) -> None:
        """Enforce per-user cooldown between vote actions.

        Args:
            user_id: UUID of the user performing the action.

        Raises:
            TooManyRequestsException: If cooldown has not elapsed.
        """
        cooldown = settings.VOTE_SKIP_COOLDOWN_SECONDS
        now = time.monotonic()
        last = _vote_cooldowns.get(user_id)
        if last is not None:
            elapsed = now - last
            if elapsed < cooldown:
                raise TooManyRequestsException(retry_after=cooldown - elapsed)
        _vote_cooldowns[user_id] = now

    async def cast_vote(self, queue_item_id: UUID, user_id: UUID) -> QueueVote:
        """Cast a skip vote for a specific queue item.

        Rejects duplicate votes from the same user on the same queue item.
        Broadcasts a skip_vote event to connected room members. If the total
        vote count reaches the room's skip threshold, triggers the finish_song
        flow to advance playback.

        Args:
            queue_item_id: UUID of the queue item to vote on.
            user_id: UUID of the user casting the vote.

        Returns:
            The newly saved QueueVote instance.

        Raises:
            EntityExistsException: If the user already voted on this item.
            TooManyRequestsException: If user is within cooldown window.
        """
        self._check_cooldown(user_id)
        existing = self._repo.get_by_item_and_user(queue_item_id, user_id)
        if existing:
            raise EntityExistsException(
                f"QueueVote: User {user_id} already voted "
                f"on queue item {queue_item_id}",
            )
        vote = QueueVote(queue_item_id=queue_item_id, user_id=user_id)
        saved_vote = self._repo.create(vote)

        await self._broadcast_and_check_skip(saved_vote)

        return saved_vote

    async def _broadcast_and_check_skip(self, vote_obj: QueueVote) -> None:
        """Broadcast skip_vote event and trigger skip if threshold reached.

        Resolves the room context from the vote's queue item chain, broadcasts
        the skip_vote event to all connected room members, and triggers
        finish_song if the vote count meets or exceeds the threshold.

        Safely returns without action if any part of the lookup chain
        (queue item, session, room) is missing.

        Args:
            vote_obj: The QueueVote that was just persisted.
        """
        queue_item = vote_obj.queue_item
        session_obj = queue_item.session
        if not session_obj:
            return

        room_obj = session_obj.room
        if not room_obj:
            return

        threshold = 2
        if room_obj.settings:
            threshold = room_obj.settings.get("skip_threshold", 2)

        current_votes = self._repo.count_by_item(vote_obj.queue_item_id)
        queue_item.votes_skip = current_votes
        skip_triggered = current_votes >= threshold

        # Run finish_song BEFORE the skip_vote broadcast so the queue has
        # already advanced when clients receive skip_triggered=true. The
        # skip_vote handler reads queue[0] to restore currentSong, and a
        # stale queue[0] would point at the song just skipped.
        if skip_triggered and self._playback_service:
            await self._playback_service.finish_song(
                session_obj.id, expected_item_id=vote_obj.queue_item_id
            )

        await manager.broadcast(
            {
                "type": "skip_vote",
                "room_id": str(room_obj.id),
                "queue_item_id": str(vote_obj.queue_item_id),
                "voter_id": str(vote_obj.user_id),
                "current_votes": current_votes,
                "threshold": threshold,
                "skip_triggered": skip_triggered,
            },
            str(room_obj.id),
        )

    async def remove_vote(self, queue_item_id: UUID, user_id: UUID) -> None:
        """Remove a previously cast skip vote (undo).

        Captures the room context from the vote's relationships before
        deletion, then broadcasts the updated (decremented) vote count.

        Args:
            queue_item_id: UUID of the queue item to remove the vote from.
            user_id: UUID of the user retracting their vote.

        Raises:
            EntityNotFoundException: If no vote exists for this user/item pair.
            TooManyRequestsException: If user is within cooldown window.
        """
        self._check_cooldown(user_id)
        existing = self._repo.get_by_item_and_user(queue_item_id, user_id)
        if not existing:
            raise EntityNotFoundException(
                f"QueueVote: No vote from user {user_id} on queue item {queue_item_id}",
            )

        queue_item = existing.queue_item
        session_obj = queue_item.session if queue_item else None
        room_obj = session_obj.room if session_obj else None

        self._repo.delete(existing)

        current_votes = self._repo.count_by_item(queue_item_id)
        if queue_item:
            queue_item.votes_skip = current_votes

        if not room_obj:
            return

        threshold = 2
        if room_obj.settings:
            threshold = room_obj.settings.get("skip_threshold", 2)

        await manager.broadcast(
            {
                "type": "skip_vote",
                "room_id": str(room_obj.id),
                "queue_item_id": str(queue_item_id),
                "voter_id": str(user_id),
                "current_votes": current_votes,
                "threshold": threshold,
                "skip_triggered": False,
            },
            str(room_obj.id),
        )

    def vote_count(self, queue_item_id: UUID) -> int:
        """Return the total number of skip votes for a queue item.

        Args:
            queue_item_id: UUID of the queue item to count votes for.

        Returns:
            The number of votes cast on this queue item.
        """
        return self._repo.count_by_item(queue_item_id)
