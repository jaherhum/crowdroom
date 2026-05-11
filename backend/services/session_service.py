"""Service for managing sessions and their playback state."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from backend.core.exceptions import EntityNotFoundException
from backend.db.models.session import Session as SessionModel
from backend.repositories.session_repo import SessionRepository
from backend.schemas.session import CreateSession, UpdateSession

if TYPE_CHECKING:
    from backend.services.playback_service import PlaybackService
    from backend.services.queue_service import QueueService


class SessionService:
    """Service for managing sessions."""

    def __init__(
        self,
        session_repo: SessionRepository,
        queue_service: Optional[QueueService] = None,
        playback_service: Optional[PlaybackService] = None,
    ) -> None:
        """Initialize the SessionService with a session repository.

        Args:
            session_repo (SessionRepository): Repository for session operations.
            queue_service (Optional[QueueService]): Queue management service.
            playback_service (Optional[PlaybackService]): Playback orchestrator service.
        """
        self._session_repo = session_repo
        self._queue_service = queue_service
        self._playback_service = playback_service

    def get_session(self, session_id: UUID) -> SessionModel:
        """Retrieve a specific session by its ID.

        Args:
            session_id (UUID): The unique identifier of the session.

        Returns:
            SessionModel: The session instance.

        Raises:
            EntityNotFoundException: If the session is not found.
        """
        session = self._session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundException("Session", session_id)
        return session

    def get_all_sessions(self) -> list[SessionModel]:
        """Retrieve all sessions.

        Returns:
            list[SessionModel]: A list of all sessions.
        """
        return self._session_repo.get_all()

    def create_session(self, session_data: CreateSession) -> SessionModel:
        """Create a new session.

        Args:
            session_data (CreateSession): The schema containing
                session creation details.

        Returns:
            SessionModel: The newly created session.
        """
        new_session = SessionModel(
            room_id=session_data.room_id,
            current_platform=session_data.current_platform,
            last_updated=datetime.now(),
        )
        return self._session_repo.create(new_session)

    def update_session(
        self,
        session_id: UUID,
        session_data: UpdateSession,
    ) -> SessionModel:
        """Update an existing session.

        Args:
            session_id (UUID): The unique identifier of the session to update.
            session_data (UpdateSession): The schema containing update details.

        Returns:
            SessionModel: The updated session instance.

        Raises:
            EntityNotFoundException: If the session does not exist.
        """
        self.get_session(session_id)
        update_data = session_data.model_dump(exclude_unset=True)
        updated_session = self._session_repo.update(session_id, update_data)
        if not updated_session:
            raise EntityNotFoundException("Session", session_id)
        return updated_session

    def delete_session(self, session_id: UUID) -> None:
        """Delete a session from the system.

        Args:
            session_id (UUID): The unique identifier of the session to delete.

        Raises:
            EntityNotFoundException: If the session is not found.
        """
        self.get_session(session_id)
        self._session_repo.delete(session_id)
