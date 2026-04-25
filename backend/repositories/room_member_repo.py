"""Repository for managing RoomMember data access."""
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db.models.room_member import RoomMember


class RoomMemberRepository:
    """Handles database operations for RoomMember."""

    async def add_member(
        self, session: AsyncSession, user_id: UUID, room_id: UUID
    ) -> RoomMember:
        """Creates a new room membership."""
        member = RoomMember(user_id=user_id, room_id=room_id)
        session.add(member)
        await session.commit()
        await session.refresh(member)
        return member

    async def remove_member(
        self, session: AsyncSession, user_id: UUID, room_id: UUID
    ) -> None:
        """Removes a room membership."""
        statement = select(RoomMember).where(
            RoomMember.user_id == user_id, RoomMember.room_id == room_id
        )
        result = await session.exec(statement)
        member = result.first()
        if member:
            await session.delete(member)
            await session.commit()

    async def get_members_by_room(
        self, session: AsyncSession, room_id: UUID
    ) -> list[RoomMember]:
        """Retrieves all members of a specific room."""
        statement = select(RoomMember).where(RoomMember.room_id == room_id)
        result = await session.exec(statement)
        return list(result.all())

    async def get_member_by_user_and_room(
        self, session: AsyncSession, user_id: UUID, room_id: UUID
    ) -> RoomMember | None:
        """Checks if a user is already in a specific room."""
        statement = select(RoomMember).where(
            RoomMember.user_id == user_id, RoomMember.room_id == room_id
        )
        result = await session.exec(statement)
        return result.first()
