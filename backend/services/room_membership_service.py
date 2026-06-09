"""Service for managing room join and leave operations."""

from uuid import UUID

from backend.api.websocket import manager
from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    UserAlreadyInRoomException,
)
from backend.db.models.room import Room
from backend.db.models.user import User
from backend.repositories.room_repo import RoomRepository
from backend.repositories.user_repo import UserRepository
from backend.services.room_invite_service import RoomInviteService
from backend.services.room_service import RoomService


class RoomMembershipService:
    """Handles user join and leave operations for rooms."""

    def __init__(
        self,
        room_service: RoomService,
        room_invite_service: RoomInviteService,
        user_repo: UserRepository,
        room_repo: RoomRepository,
    ) -> None:
        """Initialize the RoomMembershipService with its dependencies.

        Args:
            room_service: Service for room CRUD and PIN verification.
            room_invite_service: Service for invite token validation.
            user_repo: Repository for persisting user changes.
            room_repo: Repository for room data access.
        """
        self._room_service = room_service
        self._room_invite_service = room_invite_service
        self._user_repo = user_repo
        self._room_repo = room_repo

    async def join_room(
        self,
        room_id: UUID,
        user: User,
        pin: str | None = None,
        invite_token: str | None = None,
    ) -> None:
        """Join a user to a room with access control.

        Args:
            room_id: The room to join.
            user: The authenticated user.
            pin: Optional PIN for private rooms.
            invite_token: Optional invite token to bypass PIN.

        Raises:
            UserAlreadyInRoomException: If user is already in another room.
            EntityNotFoundException: If room does not exist.
            ForbiddenException: If room is private and no valid credentials.
        """
        if user.room_id is not None and user.room_id != room_id:
            raise UserAlreadyInRoomException()
        if user.room_id == room_id:
            return
        room = self._room_service.get_room(room_id)

        max_members = room.settings.get("max_members", 50)
        current_count = self._user_repo.count_by_room(room_id)
        if current_count >= max_members:
            raise ForbiddenException("Room is full")

        if room.is_private:
            # The host always has access to their own room and never needs a
            # PIN or invite to enter it.
            if room.host_user_id != user.id:
                token_ok = self._room_invite_service.validate_and_consume_invite(
                    invite_token, room_id
                )
                if not token_ok:
                    if pin and self._room_service.verify_pin(room_id, pin):
                        pass
                    else:
                        raise ForbiddenException()

        user.room_id = room_id
        self._user_repo.save(user)

        await manager.broadcast(
            {
                "type": "member_joined",
                "payload": {
                    "user_id": str(user.id),
                    "username": user.username,
                },
            },
            str(room_id),
        )

    async def leave_room(self, user: User) -> None:
        """Remove a user from their current room.

        Args:
            user: The authenticated user.

        Raises:
            EntityNotFoundException: If user is not in any room.
        """
        if user.room_id is None:
            raise EntityNotFoundException("Room membership")
        room_id = user.room_id
        room = self._room_service.get_room(room_id)
        user.room_id = None
        self._user_repo.save(user)

        await manager.broadcast(
            {
                "type": "member_left",
                "payload": {
                    "user_id": str(user.id),
                    "username": user.username,
                },
            },
            str(room_id),
        )

        if room.host_user_id == user.id:
            await self._handle_host_departure(room)

    async def _handle_host_departure(self, room: Room) -> None:
        """Close room and evict remaining members when host leaves.

        Args:
            room: The room whose host departed.
        """
        await manager.broadcast(
            {
                "type": "room_closed",
                "payload": {"reason": "host_left"},
            },
            str(room.id),
        )

        for member in room.users:
            if member.room_id == room.id:
                member.room_id = None
                self._user_repo.save(member)

        self._room_repo.delete(room.id)
