"""User management dependencies for the API."""

from fastapi import Depends
from sqlmodel import Session

from backend.core.config import settings
from backend.core.security import SecurityService
from backend.db.database import get_session
from backend.repositories.user_repo import UserRepository
from backend.services.user_service import UserService


def get_user_repo(session: Session = Depends(get_session)) -> UserRepository:
    """Dependency that provides a UserRepository instance.

    Args:
        session (Session): The database session provided by get_session.

    Returns:
        UserRepository: An instance of UserRepository.
    """
    return UserRepository(session)


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserService:
    """Dependency that provides a UserService instance.

    Args:
        user_repo (UserRepository): The repository provided by get_user_repo.

    Returns:
        UserService: An instance of UserService, instantiating
        SecurityService with settings.
    """
    return UserService(user_repo, SecurityService(settings))
