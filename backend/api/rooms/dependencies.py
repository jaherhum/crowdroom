"""Room API dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.db.database import get_session
from backend.repositories.room_repo import RoomRepository
from backend.repositories.session_repo import SessionRepository
from backend.services.room_service import RoomService


def get_room_repo(session: DBSession = Depends(get_session)) -> RoomRepository:
    """Provide a RoomRepository bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A RoomRepository instance for room data access.
    """


def get_session_repo(session: DBSession = Depends(get_session)) -> SessionRepository:
    """Provide a SessionRepository bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A SessionRepository instance for session data access.
    """


def get_room_service(
    room_repo: RoomRepository = Depends(get_room_repo),
) -> RoomService:
    """Provide a RoomService wired with its required dependencies.

    Args:
        room_repo: RoomRepository from dependency injection.

    Returns:
        A RoomService instance for room business logic.
    """
    return RoomService(room_repo)
