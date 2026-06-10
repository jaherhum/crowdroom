"""Service for managing room join and leave operations."""

import time
from uuid import UUID

from backend.api.websocket import manager
from backend.core.config import settings
from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    TooManyRequestsException,
    UserAlreadyInRoomException,
)
from backend.db.models.room import Room
from backend.db.models.user import User
from backend.repositories.room_repo import RoomRepository
from backend.repositories.user_repo import UserRepository
from backend.services.room_invite_service import RoomInviteService
from backend.services.room_service import RoomService

_pin_attempt_cooldowns: dict[UUID, float] = {}


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

    def _check_pin_cooldown(self, user_id: UUID) -> None:
        """Reject the request if the user is locked out from a recent wrong PIN.

        Args:
            user_id: UUID of the user attempting to join.

        Raises:
            TooManyRequestsException: If the cooldown window has not elapsed
                since the last failed PIN attempt.
        """
        cooldown = settings.PIN_ATTEMPT_COOLDOWN_SECONDS
        last = _pin_attempt_cooldowns.get(user_id)
        if last is None:
            return
        elapsed = time.monotonic() - last
        if elapsed < cooldown:
            raise TooManyRequestsException(retry_after=cooldown - elapsed)
        _pin_attempt_cooldowns.pop(user_id, None)

    def _record_pin_failure(self, user_id: UUID) -> None:
        """Stamp the user's most recent failed PIN attempt.

        Args:
            user_id: UUID of the user whose attempt failed.
        """
        _pin_attempt_cooldowns[user_id] = time.monotonic()

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
            TooManyRequestsException: If the user recently submitted a wrong
                PIN and the cooldown window has not yet elapsed.
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
                self._check_pin_cooldown(user.id)
                token_ok = self._room_invite_service.validate_and_consume_invite(
                    invite_token, room_id
                )
                if token_ok:
                    _pin_attempt_cooldowns.pop(user.id, None)
                else:
                    if pin and self._room_service.verify_pin(room_id, pin):
                        _pin_attempt_cooldowns.pop(user.id, None)
                    else:
                        self._record_pin_failure(user.id)
                        raise ForbiddenException("The PIN you entered is not valid")

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
