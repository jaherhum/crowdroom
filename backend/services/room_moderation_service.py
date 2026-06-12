"""Service for host moderation actions: kicking and banning room members."""

from uuid import UUID

from backend.api.websocket import manager
from backend.core.exceptions import EntityNotFoundException, ForbiddenException
from backend.repositories.room_ban_repo import RoomBanRepository
from backend.repositories.user_repo import UserRepository
from backend.schemas.room import BannedUserRead
from backend.services.room_service import RoomService


class RoomModerationService:
    """Handles host-driven kick, ban, and unban operations for rooms."""

    def __init__(
        self,
        room_service: RoomService,
        ban_repo: RoomBanRepository,
        user_repo: UserRepository,
    ) -> None:
        """Initialize the RoomModerationService with its dependencies.

        Args:
            room_service: Service for room lookups and host assertion.
            ban_repo: Repository for ban records.
            user_repo: Repository for user persistence and lookups.
        """
        self._room_service = room_service
        self._ban_repo = ban_repo
        self._user_repo = user_repo

    async def kick_user(
        self, room_id: UUID, host_user_id: UUID, target_user_id: UUID
    ) -> None:
        """Remove a member from a room without blocking re-entry.

        Args:
            room_id: The room to kick from.
            host_user_id: The user requesting the kick (must be host).
            target_user_id: The member being kicked.

        Raises:
            EntityNotFoundException: If room or target user does not exist, or
                the target is not currently in the room.
            ForbiddenException: If requester is not the host, or targets self.
        """
        target = self._prepare_target(room_id, host_user_id, target_user_id)
        if target.room_id != room_id:
            raise EntityNotFoundException("Room membership", target_user_id)
        await self._evict(room_id, target, "member_kicked")

    async def ban_user(
        self, room_id: UUID, host_user_id: UUID, target_user_id: UUID
    ) -> None:
        """Ban a user from a room and evict them if currently present.

        A banned user is blocked from rejoining until unbanned. Banning works
        even if the target is not currently in the room (preventive ban).

        Args:
            room_id: The room to ban from.
            host_user_id: The user requesting the ban (must be host).
            target_user_id: The user being banned.

        Raises:
            EntityNotFoundException: If room or target user does not exist.
            ForbiddenException: If requester is not the host, or targets self.
        """
        target = self._prepare_target(room_id, host_user_id, target_user_id)
        self._ban_repo.add(room_id, target_user_id)
        if target.room_id == room_id:
            await self._evict(room_id, target, "member_banned")
        else:
            await manager.disconnect_user(target_user_id, str(room_id))

    def unban_user(
        self, room_id: UUID, host_user_id: UUID, target_user_id: UUID
    ) -> None:
        """Lift a ban so the user can rejoin the room.

        Args:
            room_id: The room to unban in.
            host_user_id: The user requesting the unban (must be host).
            target_user_id: The user being unbanned.

        Raises:
            EntityNotFoundException: If the room does not exist.
            ForbiddenException: If requester is not the host.
        """
        self._room_service.assert_host(room_id, host_user_id)
        self._ban_repo.remove(room_id, target_user_id)

    def list_bans(self, room_id: UUID, host_user_id: UUID) -> list[BannedUserRead]:
        """List the users banned from a room.

        Args:
            room_id: The room whose bans to list.
            host_user_id: The user requesting the list (must be host).

        Returns:
            Banned users with their usernames and ban timestamps.

        Raises:
            EntityNotFoundException: If the room does not exist.
            ForbiddenException: If requester is not the host.
        """
        self._room_service.assert_host(room_id, host_user_id)
        bans = self._ban_repo.list_by_room(room_id)
        result: list[BannedUserRead] = []
        for ban in bans:
            user = self._user_repo.get_by_id(ban.user_id)
            username = user.username if user else "(unknown)"
            result.append(
                BannedUserRead(
                    user_id=ban.user_id,
                    username=username,
                    banned_at=ban.created_at,
                )
            )
        return result

    def _prepare_target(self, room_id: UUID, host_user_id: UUID, target_user_id: UUID):
        """Assert host, reject self-targeting, and load the target user.

        Args:
            room_id: The room the action applies to.
            host_user_id: The requesting host.
            target_user_id: The user being acted upon.

        Returns:
            The target User instance.

        Raises:
            EntityNotFoundException: If room or target user does not exist.
            ForbiddenException: If requester is not the host, or targets self.
        """
        self._room_service.assert_host(room_id, host_user_id)
        if target_user_id == host_user_id:
            raise ForbiddenException("The host cannot kick or ban themselves")
        target = self._user_repo.get_by_id(target_user_id)
        if target is None:
            raise EntityNotFoundException("User", target_user_id)
        return target

    async def _evict(self, room_id: UUID, target, event_type: str) -> None:
        """Clear a user's room, announce it, and force-close their socket.

        Args:
            room_id: The room being left.
            target: The User being evicted.
            event_type: The broadcast event ('member_kicked' or 'member_banned').
        """
        target.room_id = None
        self._user_repo.save(target)
        await manager.broadcast(
            {
                "type": event_type,
                "payload": {
                    "user_id": str(target.id),
                    "username": target.username,
                },
            },
            str(room_id),
        )
        await manager.disconnect_user(target.id, str(room_id))
