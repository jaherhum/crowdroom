"""Room API dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.api.invites.dependencies import get_invite_service
from backend.api.users.dependencies import get_user_repo
from backend.core.config import settings
from backend.core.security import SecurityService
from backend.db.database import get_session
from backend.repositories.room_repo import RoomRepository
from backend.repositories.session_repo import SessionRepository
from backend.repositories.user_repo import UserRepository
from backend.services.room_invite_service import RoomInviteService
from backend.services.room_membership_service import RoomMembershipService
from backend.services.room_service import RoomService


def get_room_repo(session: DBSession = Depends(get_session)) -> RoomRepository:
    """Provide a RoomRepository bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A RoomRepository instance for room data access.
    """
    return RoomRepository(session)


def get_session_repo(session: DBSession = Depends(get_session)) -> SessionRepository:
    """Provide a SessionRepository bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A SessionRepository instance for session data access.
    """
    return SessionRepository(session)


def get_room_service(
    room_repo: RoomRepository = Depends(get_room_repo),
) -> RoomService:
    """Provide a RoomService wired with its required dependencies.

    Args:
        room_repo: RoomRepository from dependency injection.

    Returns:
        A RoomService instance for room business logic.
    """
    return RoomService(room_repo, SecurityService(settings))

def get_room_membership_service(
    room_service: RoomService = Depends(get_room_service),
    invite_service: RoomInviteService = Depends(get_invite_service),
    user_repo: UserRepository = Depends(get_user_repo),
    room_repo: RoomRepository = Depends(get_room_repo),
) -> RoomMembershipService:
    """Provide a RoomMembershipService wired with its required dependencies.

    Args:
        room_service: RoomService from dependency injection.
        invite_service: RoomInviteService from dependency injection.
        user_repo: UserRepository from dependency injection.
        room_repo: RoomRepository from dependency injection.

    Returns:
        A RoomMembershipService instance for join/leave operations.
    """
    return RoomMembershipService(room_service, invite_service, user_repo, room_repo)
