"""Repository for PlatformConnection."""
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession, select

from backend.db.models import PlatformConnection, StreamingPlatforms


class PlatformConnectionRepo:
    """"""

    def __init__(self, session: DBSession):
        self._session = session

    def create(self, connection: PlatformConnection) -> PlatformConnection:
        try:
            self._session.add(connection)
            self._session.commit()
            self._session.refresh(connection)
            return connection
        except IntegrityError:
            self._session.rollback()
            raise

    def get_by_id(self, connection_id: UUID) -> PlatformConnection | None:
        return self._session.get(PlatformConnection, connection_id)

    def get_by_user_and_platform(self, user_id: UUID, platform: StreamingPlatforms) -> PlatformConnection | None:
        return self._session.exec(
            select(PlatformConnection).where(
                PlatformConnection.user_id == user_id, PlatformConnection.platform == platform)
            ).first()

    def get_all_by_user(self, user_id: UUID) -> list[PlatformConnection]:
        return self._session.exec(
            select(PlatformConnection).where(
                PlatformConnection.user_id == user_id
            )
        ).all()

    def delete(self, connection_id: UUID) -> None:
        connection = self._session.get(PlatformConnection, connection_id)

        if connection:
            try:
                self._session.delete(connection)
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise