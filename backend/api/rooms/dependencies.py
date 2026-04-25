"""Room API dependencies."""

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db.database import get_session
from backend.repositories.room_member_repo import RoomMemberRepository
from backend.repositories.room_repo import RoomRepository
from backend.services.room_service import RoomService


def get_room_repo(session: AsyncSession = Depends(get_session)) -> RoomRepository:
    """Dependency that provides a RoomRepository instance."""
    return RoomRepository(session)


def get_room_member_repo(
    session: AsyncSession = Depends(get_session)
) -> RoomMemberRepository:
    """Dependency that provides a RoomMemberRepository instance."""
    return RoomMemberRepository(session)


def get_room_service(
    room_repo: RoomRepository = Depends(get_room_repo),
    room_member_repo: RoomMemberRepository = Depends(get_room_member_repo),
) -> RoomService:
    """Dependency that provides a RoomService instance."""
    return RoomService(room_repo, room_member_repo)
