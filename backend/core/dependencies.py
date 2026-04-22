"""Core dependencies for the application."""

from fastapi import Depends
from sqlmodel import Session

from backend.db.database import get_session
from backend.repositories.user_repo import UserRepository
from backend.services.user_service import UserService


def get_user_repo(session: Session = Depends(get_session)) -> UserRepository:
    """Provides a UserRepository instance.

    Args:
        session (Session): The database session.

    Returns:
        UserRepository: An instance of UserRepository.
    """
    return UserRepository(session)


def get_user_service(user_repo: UserRepository = Depends(get_user_repo)) -> UserService:
    """Provides a UserService instance.

    Args:
        user_repo (UserRepository): The repository instance.

    Returns:
        UserService: An instance of UserService.
    """
    from backend.core.config import settings
    from backend.core.security import SecurityService

    return UserService(user_repo, SecurityService(settings))
