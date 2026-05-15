"""Repository for QueueVote data access."""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import select

from backend.db.models import QueueVote


class QueueVoteRepository:
    """Data access layer for queue votes."""

    def __init__(self, session: DBSession) -> None:
        """Initialize the QueueVoteRepository with a database session.

        Args:
            session: Database session for all CRUD operations.
        """
        self._session = session

    def create(self, vote: QueueVote) -> QueueVote:
        """Persist a new skip vote to the database.

        Raises:
            IntegrityError: If unique constraint violated (duplicate vote).
        """
        try:
            self._session.add(vote)
            self._session.commit()
            self._session.refresh(vote)
            return vote
        except IntegrityError:
            self._session.rollback()
            raise

    def get_by_item_and_user(
        self, queue_item_id: UUID, user_id: UUID
    ) -> QueueVote | None:
        """Look up an existing vote by queue item and voter.

        Args:
            queue_item_id: The UUID of the queue item that was voted on.
            user_id: The UUID of the user who cast the vote.

        Returns:
            The QueueVote if found, otherwise None.
        """
        stmt = select(QueueVote).where(
            QueueVote.queue_item_id == queue_item_id,
            QueueVote.user_id == user_id,
        )
        return self._session.exec(stmt).first()

    def count_by_item(self, queue_item_id: UUID) -> int:
        """Count the total number of votes for a specific queue item.

        Args:
            queue_item_id: The UUID of the queue item to count votes for.

        Returns:
            The number of votes cast on this queue item.
        """
        stmt = select(func.count()).where(QueueVote.queue_item_id == queue_item_id)
        return self._session.exec(stmt).one()

    def delete_by_item(self, queue_item_id: UUID) -> None:
        """Remove all votes associated with a specific queue item.

        Args:
            queue_item_id: The UUID of the queue item whose votes to delete.
        """
        stmt = select(QueueVote).where(QueueVote.queue_item_id == queue_item_id)
        votes = self._session.exec(stmt).all()
        for vote in votes:
            self._session.delete(vote)
        if votes:
            try:
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise

    def get_by_id(self, vote_id: UUID) -> QueueVote | None:
        """Fetch a single queue vote by its primary key.

        Args:
            vote_id: The UUID of the vote to retrieve.

        Returns:
            The QueueVote if found, otherwise None.
        """
        stmt = select(QueueVote).where(QueueVote.id == vote_id)
        return self._session.exec(stmt).first()
