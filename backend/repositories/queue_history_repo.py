"""Repository for QueueHistory data access."""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import select

from backend.db.models import QueueHistory


class QueueHistoryRepository:
    """Data access layer for playback history."""

    def __init__(self, session: DBSession) -> None:
        """Initialize the QueueHistoryRepository with a database session.

        Args:
            session: Database session for all CRUD operations.
        """
        self._session = session

    def create(self, history: QueueHistory) -> QueueHistory:
        """Persist a new playback history entry to the database.

        Raises:
            IntegrityError: If a unique constraint is violated.
        """
        try:
            self._session.add(history)
            self._session.commit()
            self._session.refresh(history)
            return history
        except IntegrityError:
            self._session.rollback()
            raise

    def get_all_by_session(
        self, session_id: UUID, limit: int = 15
    ) -> list[QueueHistory]:
        """Retrieve playback history for a session, ordered newest first.

        Args:
            session_id: The session whose history to retrieve.
            limit: Maximum number of entries to return (default 15).

        Returns:
            A list of QueueHistory records ordered by played_at descending.
        """
        stmt = (
            select(QueueHistory)
            .where(QueueHistory.session_id == session_id)
            .order_by(QueueHistory.played_at.desc())
            .limit(limit)
        )
        return self._session.exec(stmt).all()

    def count_by_session(self, session_id: UUID) -> int:
        """Count total playback history entries for a session.

        Args:
            session_id: The session whose history to count.

        Returns:
            The number of history records for the given session.
        """
        stmt = select(func.count()).where(QueueHistory.session_id == session_id)
        return self._session.exec(stmt).one()

    def delete_oldest(self, session_id: UUID, keep: int = 15) -> None:
        """Remove excess playback history, preserving only the most recent entries.

        Args:
            session_id: The session whose history to prune.
            keep: Number of newest entries to retain (default 15).
        """
        stmt = (
            select(QueueHistory)
            .where(QueueHistory.session_id == session_id)
            .order_by(QueueHistory.played_at.asc())
            .offset(keep)
        )
        old_entries = self._session.exec(stmt).all()
        for entry in old_entries:
            self._session.delete(entry)
        if old_entries:
            try:
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise

    def get_by_session(self, session_id: UUID, limit: int = 15) -> list[QueueHistory]:
        """Retrieve playback history for a session, ordered newest first.

        Args:
            session_id: The session whose history to retrieve.
            limit: Maximum number of entries to return (default 15).

        Returns:
            A list of QueueHistory records ordered by played_at descending.
        """
        stmt = (
            select(QueueHistory)
            .where(QueueHistory.session_id == session_id)
            .order_by(QueueHistory.played_at.desc())
            .limit(limit)
        )
        return self._session.exec(stmt).all()
