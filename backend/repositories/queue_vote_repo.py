"""Repository for QueueVote data access."""
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session as DBSession, select

from backend.db.models import QueueVote


class QueueVoteRepository:
    """Data access layer for queue votes."""

    def __init__(self, session: DBSession) -> None:
        self._session = session

    def create(self, vote: QueueVote) -> QueueVote:
        """Create a new skip vote."""
        self._session.add(vote)
        self._session.commit()
        self._session.refresh(vote)
        return vote

    def get_by_item_and_user(
        self, queue_item_id: UUID, user_id: UUID
    ) -> QueueVote | None:
        """Check if a specific user already voted on a specific queue item."""
        stmt = select(QueueVote).where(
            QueueVote.queue_item_id == queue_item_id,
            QueueVote.user_id == user_id,
        )
        return self._session.exec(stmt).first()

    def count_by_item(self, queue_item_id: UUID) -> int:
        """Count the total number of votes for a specific queue item."""
        stmt = select(func.count()).where(QueueVote.queue_item_id == queue_item_id)
        return self._session.exec(stmt).one()

    def delete_by_item(self, queue_item_id: UUID) -> None:
        """Remove all votes associated with a specific queue item."""
        stmt = select(QueueVote).where(QueueVote.queue_item_id == queue_item_id)
        votes = self._session.exec(stmt).all()
        for vote in votes:
            self._session.delete(vote)
        self._session.commit()
