"""Repository for QueueItem data access."""

from uuid import UUID

from sqlalchemy import case, func, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import select

from backend.db.models import QueueItem


def _immediate_begin(session: DBSession) -> None:
    """Acquire an exclusive SQLite write lock.

    SQLite's default transaction (BEGIN DEFERRED) allows concurrent readers,
    which breaks atomicity when multiple threads read-then-write.
    BEGIN IMMEDIATE acquires a reserved lock immediately, ensuring that
    only one thread can execute read+write at a time.

    For PostgreSQL this is a no-op since PG uses MVCC and all operations
    within the session's transaction are already atomic.
    """
    try:
        session.execute(text("BEGIN IMMEDIATE"))
    except Exception:
        # On PostgreSQL or other DBs without BEGIN IMMEDIATE, ignore
        pass


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

    def delete(self, queue_item_id: UUID) -> bool:
        """Delete a queue item by ID.

        Uses BEGIN IMMEDIATE to acquire an exclusive write lock before
        checking existence and deleting — prevents TOCTOU race where
        multiple threads all read the item as existing simultaneously.

        Returns:
            True if the item was deleted, False if it didn't exist.
        """
        _immediate_begin(self._session)
        queue_item = self._session.get(QueueItem, queue_item_id)
        if queue_item:
            try:
                self._session.delete(queue_item)
                self._session.commit()
                return True
            except IntegrityError:
                self._session.rollback()
                raise
        return False

    def add_to_queue_atomic(
        self,
        session_id: UUID,
        song_id: UUID,
        added_by_user_id: UUID | None = None,
        group: str = "manual",
    ) -> QueueItem:
        """Atomically read max position and create a new queue item.

        Uses BEGIN IMMEDIATE to acquire an exclusive SQLite write lock
        (or PostgreSQL's default serializable transaction), ensuring that
        no two threads can read the same max position simultaneously.

        Raises:
            IntegrityError: If a unique constraint on
                (session_id, position, group) is violated.
        """
        _immediate_begin(self._session)

        stmt = select(func.coalesce(func.max(QueueItem.position), -1)).where(
            QueueItem.session_id == session_id,
            QueueItem.group == group,
        )
        max_pos = self._session.exec(stmt).one()

        queue_item = QueueItem(
            session_id=session_id,
            song_id=song_id,
            added_by_user_id=added_by_user_id,
            position=max_pos + 1,
            group=group,
        )
        self._session.add(queue_item)
        self._session.commit()

        # Refresh outside the transaction to get back the generated PK
        self._session.refresh(queue_item)
        return queue_item

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
        stmt = select(func.coalesce(func.max(QueueItem.position), -1)).where(
            QueueItem.session_id == session_id, QueueItem.group == group
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
