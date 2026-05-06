"""Service for managing skip votes on queue items."""

from uuid import UUID

from backend.core.exceptions import EntityExistsException
from backend.db.models.queue_vote import QueueVote
from backend.repositories.queue_vote_repo import QueueVoteRepository


class QueueVoteService:
    """Service for managing skip votes."""

    def __init__(self, queue_vote_repo: QueueVoteRepository) -> None:
        self._repo = queue_vote_repo

    def cast_vote(self, queue_item_id: UUID, user_id: UUID) -> QueueVote:
        """Cast a skip vote. Raises if user already voted."""
        existing = self._repo.get_by_item_and_user(queue_item_id, user_id)
        if existing:
            raise EntityExistsException(
                f"QueueVote: User {user_id} already voted "
                f"on queue item {queue_item_id}",
            )
        vote = QueueVote(queue_item_id=queue_item_id, user_id=user_id)
        return self._repo.create(vote)

    def vote_count(self, queue_item_id: UUID) -> int:
        """Get the number of votes for a queue item."""
        return self._repo.count_by_item(queue_item_id)
