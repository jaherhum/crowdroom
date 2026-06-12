"""Service for managing room invite links."""

from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    InviteExpiredException,
    UserAlreadyInRoomException,
)
from backend.core.invite_token import generate_invite_token
from backend.db.models.room_invite import RoomInvite
from backend.db.models.user import User
from backend.repositories.room_invite_repo import RoomInviteRepository
from backend.repositories.room_repo import RoomRepository
from backend.repositories.user_repo import UserRepository
from backend.schemas.room_invite import (
    CreateRoomInvite,
    InviteJoinResult,
    InvitePreview,
)
from backend.services.room_service import RoomService

MAX_TOKEN_RETRIES = 5


class RoomInviteService:
    """Service for creating, validating, and redeeming room invites."""

    def __init__(
        self,
        invite_repo: RoomInviteRepository,
        room_repo: RoomRepository,
        user_repo: UserRepository,
        room_service: RoomService,
    ) -> None:
        """Initialize the RoomInviteService with its dependencies.

        Args:
            invite_repo: Repository for invite data operations.
            room_repo: Repository for room lookups.
            user_repo: Repository for user updates on join.
            room_service: Service for room operations including host verification.
        """
        self._invite_repo = invite_repo
        self._room_repo = room_repo
        self._user_repo = user_repo
        self._room_service = room_service

    def _validate_invite(self, invite: RoomInvite) -> None:
        """Check that an invite is still valid (not expired or exhausted).

        Args:
            invite: The invite to validate.

        Raises:
            InviteExpiredException: If invite is expired or has reached max uses.
        """
        now = datetime.now(timezone.utc)
        expires_at = invite.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and expires_at <= now:
            raise InviteExpiredException()
        if invite.max_uses is not None and invite.use_count >= invite.max_uses:
            raise InviteExpiredException()

    def create_invite(
        self,
        room_id: UUID,
        user_id: UUID,
        data: CreateRoomInvite,
        token_factory: Callable[[], str] = generate_invite_token,
    ) -> RoomInvite:
        """Create a new invite link for a room.

        Args:
            room_id: The room to create an invite for.
            user_id: The requesting user (must be host).
            data: Invite creation parameters.
            token_factory: Callable returning a token string. Defaults to
                the standard 12-char generator. Pass `generate_long_invite_token`
                for harder-to-guess QR invites.

        Returns:
            The created RoomInvite.

        Raises:
            EntityNotFoundException: If room does not exist.
            ForbiddenException: If user is not the room host.
            IntegrityError: If token generation exhausts all retries.
        """
        self._room_service.assert_host(room_id, user_id)

        expires_at = None
        if data.expires_in_hours is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=data.expires_in_hours
            )

        for attempt in range(MAX_TOKEN_RETRIES + 1):
            invite = RoomInvite(
                room_id=room_id,
                token=token_factory(),
                max_uses=data.max_uses,
                expires_at=expires_at,
            )
            try:
                return self._invite_repo.create(invite)
            except IntegrityError:
                if attempt == MAX_TOKEN_RETRIES:
                    raise

    def get_invite_preview(self, token: str) -> InvitePreview:
        """Validate an invite token and return room preview info.

        Args:
            token: The invite token to look up.

        Returns:
            Preview information about the room.

        Raises:
            EntityNotFoundException: If token does not exist.
            InviteExpiredException: If invite is expired or exhausted.
        """
        invite = self._invite_repo.get_by_token(token)
        if not invite:
            raise EntityNotFoundException("Invite", token)
        self._validate_invite(invite)

        room = self._room_repo.get_by_id(invite.room_id)
        if not room:
            raise EntityNotFoundException("Room", invite.room_id)

        return InvitePreview(
            room_id=room.id,
            room_name=room.room_name,
            is_private=room.is_private,
            host_user_id=room.host_user_id,
        )

    def join_via_invite(self, token: str, user: User) -> InviteJoinResult:
        """Join a room using an invite token, bypassing PIN check.

        Args:
            token: The invite token to redeem.
            user: The authenticated user joining the room.

        Returns:
            Result containing the joined room info.

        Raises:
            EntityNotFoundException: If token or room does not exist.
            InviteExpiredException: If invite is expired or exhausted.
        """
        invite = self._invite_repo.get_by_token(token)
        if not invite:
            raise EntityNotFoundException("Invite", token)
        self._validate_invite(invite)

        room = self._room_repo.get_by_id(invite.room_id)
        if not room:
            raise EntityNotFoundException("Room", invite.room_id)

        if user.room_id is not None and user.room_id != room.id:
            raise UserAlreadyInRoomException(user.room_id)
        user.room_id = room.id
        self._user_repo.save(user)
        self._invite_repo.increment_use_count(invite)

        return InviteJoinResult(room_id=room.id, room_name=room.room_name)

    def list_invites(self, room_id: UUID, user_id: UUID) -> list[RoomInvite]:
        """List all invites for a room (host only).

        Args:
            room_id: The room to list invites for.
            user_id: The requesting user (must be host).

        Returns:
            List of RoomInvite instances.

        Raises:
            EntityNotFoundException: If room does not exist.
            ForbiddenException: If user is not the room host.
        """
        self._room_service.assert_host(room_id, user_id)
        return self._invite_repo.get_by_room(room_id)

    def revoke_invite(self, room_id: UUID, invite_id: UUID, user_id: UUID) -> None:
        """Revoke (delete) a specific invite.

        Args:
            room_id: The room the invite belongs to.
            invite_id: The invite to revoke.
            user_id: The requesting user (must be host).

        Raises:
            EntityNotFoundException: If room or invite does not exist.
            ForbiddenException: If user is not the room host or invite
                doesn't belong to the room.
        """
        self._room_service.assert_host(room_id, user_id)

        invite = self._invite_repo.get_by_id(invite_id)
        if not invite:
            raise EntityNotFoundException("Invite", invite_id)
        if invite.room_id != room_id:
            raise ForbiddenException("Invite does not belong to this room")

        self._invite_repo.delete(invite_id)

    def validate_and_consume_invite(self, token: str, expected_room_id: UUID) -> bool:
        """Validate invite token for a specific room and increment use count.

        Args:
            token: The invite token to check.
            expected_room_id: The room the invite must belong to.

        Returns:
            True if invite is valid for given room, False otherwise.
        """
        invite = self._invite_repo.get_by_token(token)
        if not invite or invite.room_id != expected_room_id:
            return False
        try:
            self._validate_invite(invite)
            self._invite_repo.increment_use_count(invite)
            return True
        except InviteExpiredException:
            return False
