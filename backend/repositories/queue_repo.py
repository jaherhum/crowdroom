"""Repository for QueueItem data access."""
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import select

from backend.db.models import QueueItem


class QueueRepository:
    """Data access layer for queue items."""

    def __init__(self, session: DBSession) -> None:
        self._session = session

    def create(self, queue_item: QueueItem) -> QueueItem:
        """Create a new queue item.

        Raises:
            IntegrityError: If unique constraint violated (duplicate position).
        """
        try:
            self._session.add(queue_item)
            self._session.commit()
            self._session.refresh(queue_item)
            return queue_item
        except IntegrityError:
            self._session.rollback()
            raise

    def delete(self, queue_item_id: UUID) -> None:
        """Delete a queue item by ID."""
        queue_item = self._session.get(QueueItem, queue_item_id)
        if queue_item:
            try:
                self._session.delete(queue_item)
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise

    def get_by_id(self, queue_item_id: UUID) -> QueueItem | None:
        """Retrieve a queue item by its ID."""
        return self._session.get(QueueItem, queue_item_id)

    def get_all_by_session(self, session_id: UUID) -> list[QueueItem]:
        """Retrieve all queue items for a session.

        Ordered by group priority then position.

        """
        stmt = (
            select(QueueItem)
            .where(QueueItem.session_id == session_id)
            .order_by(
                case((QueueItem.group == "manual", 0), else_=1),
                QueueItem.position,
            )
        )
        return self._session.exec(stmt).all()

    def get_max_position_in_group(self, session_id: UUID, group: str) -> int:
        """Get the maximum position within a specific group for a session.

        Returns -1 if the group is empty.
        """
        stmt = (
            select(func.coalesce(func.max(QueueItem.position), -1))
            .where(QueueItem.session_id == session_id, QueueItem.group == group)
        )
        return self._session.exec(stmt).one()

    def get_first_item(self, session_id: UUID) -> QueueItem | None:
        """Get the first item (position 0) in a session's queue."""
        stmt = select(QueueItem).where(
            QueueItem.session_id == session_id,
            QueueItem.position == 0,
        )
        return self._session.exec(stmt).first()

    def get_by_session_and_position(
        self, session_id: UUID, position: int
    ) -> QueueItem | None:
        """Get a queue item at a specific position within a session."""
        stmt = select(QueueItem).where(
            QueueItem.session_id == session_id,
            QueueItem.position == position,
        )
        return self._session.exec(stmt).first()

    def count_by_session(self, session_id: UUID) -> int:
        """Count the total number of items in a session's queue."""
        stmt = select(func.count()).where(QueueItem.session_id == session_id)
        return self._session.exec(stmt).one()
