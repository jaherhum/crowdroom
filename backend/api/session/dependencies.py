"""Session API dependencies."""

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.db.database import get_session
from backend.repositories.session_repo import SessionRepository
from backend.services.session_service import SessionService


def get_session_repo(session: DBSession = Depends(get_session)) -> SessionRepository:
    """Dependency that provides a SessionRepository instance."""
    return SessionRepository(session)


def get_session_service(
    session_repo: SessionRepository = Depends(get_session_repo),
) -> SessionService:
    """Dependency that provides a SessionService instance."""
    return SessionService(session_repo)
