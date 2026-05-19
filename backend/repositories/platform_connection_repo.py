"""Repository for PlatformConnection."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import select

from backend.db.models import PlatformConnection, StreamingPlatforms


class PlatformConnectionRepo:
    """Data access layer for platform connection records."""

    def __init__(self, session: DBSession):
        self._session = session

    def create(self, connection: PlatformConnection) -> PlatformConnection:
        """Persist a new platform connection.

        Args:
            connection: PlatformConnection instance to store.

        Returns:
            Refreshed connection with generated ID.

        Raises:
            IntegrityError: If user+platform combination already exists.
        """
        try:
            self._session.add(connection)
            self._session.commit()
            self._session.refresh(connection)
            return connection
        except IntegrityError:
            self._session.rollback()
            raise

    def get_by_id(self, connection_id: UUID) -> PlatformConnection | None:
        """Retrieve a connection by its primary key.

        Args:
            connection_id: UUID of the connection.

        Returns:
            PlatformConnection if found, None otherwise.
        """
        return self._session.get(PlatformConnection, connection_id)

    def get_by_user_and_platform(
        self, user_id: UUID, platform: StreamingPlatforms
    ) -> PlatformConnection | None:
        """Find a user's connection for a specific platform.

        Args:
            user_id: UUID of the owning user.
            platform: Target streaming platform.

        Returns:
            PlatformConnection if found, None otherwise.
        """
        return self._session.exec(
            select(PlatformConnection).where(
                PlatformConnection.user_id == user_id,
                PlatformConnection.platform == platform,
            )
        ).first()

    def get_all_by_user(self, user_id: UUID) -> list[PlatformConnection]:
        """Retrieve all platform connections for a user.

        Args:
            user_id: UUID of the owning user.

        Returns:
            List of PlatformConnection records (may be empty).
        """
        return self._session.exec(
            select(PlatformConnection).where(PlatformConnection.user_id == user_id)
        ).all()

    def delete(self, connection_id: UUID) -> None:
        """Delete a platform connection by ID.

        Args:
            connection_id: UUID of the connection to remove.
        """
        connection = self._session.get(PlatformConnection, connection_id)

        if connection:
            try:
                self._session.delete(connection)
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise
