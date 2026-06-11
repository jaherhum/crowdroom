"""Dependency injection for room invite endpoints."""

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.api.rooms.dependencies import get_room_repo, get_room_service
from backend.api.users.dependencies import get_user_repo
from backend.core.config import settings
from backend.db.database import get_session
from backend.repositories.room_invite_repo import RoomInviteRepository
from backend.repositories.room_repo import RoomRepository
from backend.repositories.user_repo import UserRepository
from backend.services.invite_qr_service import InviteQRService
from backend.services.room_invite_service import RoomInviteService
from backend.services.room_service import RoomService


def get_invite_repo(
    session: DBSession = Depends(get_session),
) -> RoomInviteRepository:
    """Provide a RoomInviteRepository bound to the current database session."""
    return RoomInviteRepository(session)


def get_invite_service(
    invite_repo: RoomInviteRepository = Depends(get_invite_repo),
    room_repo: RoomRepository = Depends(get_room_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    room_service: RoomService = Depends(get_room_service),
) -> RoomInviteService:
    """Provide a RoomInviteService wired with its required dependencies."""
    return RoomInviteService(invite_repo, room_repo, user_repo, room_service)


def get_invite_qr_service(
    invite_service: RoomInviteService = Depends(get_invite_service),
) -> InviteQRService:
    """Provide an InviteQRService wired with its required dependencies."""
    return InviteQRService(invite_service, settings)
