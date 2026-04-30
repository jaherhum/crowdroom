from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from backend.db.models import QueueItem


class QueueRepository:

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, queue_item: QueueItem) -> QueueItem:
        self._session.add(queue_item)
        self._session.commit()
        self._session.refresh(queue_item)
        return queue_item

    def delete(self, queue_item_id: UUID) -> None:
        queue_item = self.get_by_id(queue_item_id)
        if queue_item:
            self._session.delete(queue_item)
            self._session.commit()

    def get_by_id(self, queue_item_id: UUID) -> QueueItem | None:
        return self._session.get(QueueItem, queue_item_id)

    def get_all_by_room(self, room_id: UUID) -> list[QueueItem]:
        stmt = select(QueueItem).where(
            QueueItem.room_id == room_id
        ).order_by(QueueItem.position)
        return self._session.exec(stmt).all()

    def get_max_position(self, room_id: UUID) -> int:
        stmt = select(
            func.coalesce(func.max(QueueItem.position), -1)
        ).where(
            QueueItem.room_id == room_id
        )
        return self._session.exec(stmt).one()