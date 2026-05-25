"""Dependency injection for room invite endpoints."""

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.api.rooms.dependencies import get_room_repo
from backend.api.users.dependencies import get_user_repo
from backend.db.database import get_session
from backend.repositories.room_invite_repo import RoomInviteRepository
from backend.repositories.room_repo import RoomRepository
from backend.repositories.user_repo import UserRepository
from backend.services.room_invite_service import RoomInviteService


def get_invite_repo(
    session: DBSession = Depends(get_session),
) -> RoomInviteRepository:
    """Provide a RoomInviteRepository bound to the current database session."""
    return RoomInviteRepository(session)


def get_invite_service(
    invite_repo: RoomInviteRepository = Depends(get_invite_repo),
    room_repo: RoomRepository = Depends(get_room_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> RoomInviteService:
    """Provide a RoomInviteService wired with its required dependencies."""
    return RoomInviteService(invite_repo, room_repo, user_repo)
