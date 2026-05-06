"""Repository for Session data access."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession, select

from backend.db.models.session import Session as SessionModel


class SessionRepository:
    """Handles database operations for Sessions."""

    def __init__(self, db_session: DBSession):
        """Initializes the repository with a database session."""
        self._session = db_session

    def create(self, session: SessionModel) -> SessionModel:
        """Creates a new session in the database.

        Args:
            session (SessionModel): The session instance to create.

        Returns:
            SessionModel: The created session.

        Raises:
            IntegrityError: If a unique constraint is violated (duplicate room_id).
        """
        try:
            self._session.add(session)
            self._session.commit()
            self._session.refresh(session)
            return session
        except IntegrityError:
            self._session.rollback()
            raise

    def get_by_id(self, session_id: UUID) -> SessionModel | None:
        """Retrieves a session by its ID.

        Args:
            session_id (UUID): The unique identifier of the session.

        Returns:
            SessionModel | None: The session instance if found, otherwise None.
        """
        return self._session.get(SessionModel, session_id)

    def get_by_room(self, room_id: UUID) -> SessionModel | None:
        """Retrieves the session for a specific room.

        Args:
            room_id (UUID): The unique identifier of the room.

        Returns:
            SessionModel | None: The session instance if found, otherwise None.
        """
        return self._session.exec(
            select(SessionModel).where(SessionModel.room_id == room_id)
        ).first()

    def get_all(self) -> list[SessionModel]:
        """Retrieves all sessions in the database.

        Returns:
            list[SessionModel]: A list of all sessions.
        """
        return self._session.exec(select(SessionModel)).all()

    def update(self, session_id: UUID, update_data: dict) -> SessionModel | None:
        """Updates an existing session with the provided data.

        Args:
            session_id (UUID): The unique identifier of the session.
            update_data (dict): A dictionary containing the fields to update.

        Returns:
            SessionModel | None: The updated session instance if found, otherwise None.

        Raises:
            IntegrityError: If a unique constraint is violated.
        """
        session = self._session.get(SessionModel, session_id)
        if session:
            for key, value in update_data.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            try:
                self._session.add(session)
                self._session.commit()
                self._session.refresh(session)
                return session
            except IntegrityError:
                self._session.rollback()
                raise
        return None

    def delete(self, session_id: UUID) -> None:
        """Deletes a session from the database.

        Args:
            session_id (UUID): The unique identifier of the session to delete.
        """
        session = self._session.get(SessionModel, session_id)
        if session:
            try:
                self._session.delete(session)
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise
