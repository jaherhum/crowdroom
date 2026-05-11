"""Room API dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.db.database import get_session
from backend.repositories.room_repo import RoomRepository
from backend.repositories.session_repo import SessionRepository
from backend.services.room_service import RoomService


def get_room_repo(session: DBSession = Depends(get_session)) -> RoomRepository:
    """Dependency that provides a RoomRepository instance."""
    return RoomRepository(session)


def get_session_repo(session: DBSession = Depends(get_session)) -> SessionRepository:
    """Dependency that provides a SessionRepository instance."""
    return SessionRepository(session)


def get_room_service(
    room_repo: RoomRepository = Depends(get_room_repo),
) -> RoomService:
    """Dependency that provides a RoomService instance."""
    return RoomService(room_repo)
