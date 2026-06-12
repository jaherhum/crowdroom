"""Platform connections API dependencies."""

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.db.database import get_session
from backend.repositories.platform_connection_repo import PlatformConnectionRepo
from backend.services.platform_connection_service import PlatformConnectionService


def get_platform_connection_repo(
    session: DBSession = Depends(get_session),
) -> PlatformConnectionRepo:
    """Provide a PlatformConnectionRepo bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A PlatformConnectionRepo instance.
    """
    return PlatformConnectionRepo(session)


def get_platform_connection_service(
    repo: PlatformConnectionRepo = Depends(get_platform_connection_repo),
) -> PlatformConnectionService:
    """Provide a PlatformConnectionService wired with its repository.

    Args:
        repo: PlatformConnectionRepo from dependency injection.

    Returns:
        A PlatformConnectionService instance.
    """
    return PlatformConnectionService(repo)
