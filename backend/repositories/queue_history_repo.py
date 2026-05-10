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
        self._session = session

    def create(self, history: QueueHistory) -> QueueHistory:
        """Create a new playback history entry.

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
        """Retrieve history for a session, newest first."""
        stmt = (
            select(QueueHistory)
            .where(QueueHistory.session_id == session_id)
            .order_by(QueueHistory.played_at.desc())
            .limit(limit)
        )
        return self._session.exec(stmt).all()

    def count_by_session(self, session_id: UUID) -> int:
        """Count total history entries for a session."""
        stmt = select(func.count()).where(QueueHistory.session_id == session_id)
        return self._session.exec(stmt).one()

    def delete_oldest(self, session_id: UUID, keep: int = 15) -> None:
        """Prune old history entries, keeping the newest keep entries."""
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
        """Retrieve history for a session, newest first."""
        stmt = (
            select(QueueHistory)
            .where(QueueHistory.session_id == session_id)
            .order_by(QueueHistory.played_at.desc())
            .limit(limit)
        )
        return self._session.exec(stmt).all()
