"""Repository for RoomBan data access."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import select

from backend.db.models.room_ban import RoomBan


class RoomBanRepository:
    """Handles database operations for RoomBans."""

    def __init__(self, session: DBSession):
        """Initialize the RoomBanRepository with a database session.

        Args:
            session: Database session for all CRUD operations on room bans.
        """
        self._session = session

    def add(self, room_id: UUID, user_id: UUID) -> RoomBan:
        """Ban a user from a room, idempotently.

        Args:
            room_id: The room the ban applies to.
            user_id: The user to ban.

        Returns:
            The RoomBan row, whether newly created or already existing.
        """
        existing = self._get(room_id, user_id)
        if existing is not None:
            return existing
        ban = RoomBan(room_id=room_id, user_id=user_id)
        try:
            self._session.add(ban)
            self._session.commit()
            self._session.refresh(ban)
            return ban
        except IntegrityError:
            # Lost a race against a concurrent ban; the row now exists.
            self._session.rollback()
            return self._get(room_id, user_id)

    def remove(self, room_id: UUID, user_id: UUID) -> bool:
        """Lift a ban for a user in a room.

        Args:
            room_id: The room the ban applies to.
            user_id: The banned user.

        Returns:
            True if a ban was removed, False if none existed.
        """
        ban = self._get(room_id, user_id)
        if ban is None:
            return False
        try:
            self._session.delete(ban)
            self._session.commit()
            return True
        except IntegrityError:
            self._session.rollback()
            raise

    def exists(self, room_id: UUID, user_id: UUID) -> bool:
        """Check whether a user is banned from a room.

        Args:
            room_id: The room to check.
            user_id: The user to check.

        Returns:
            True if a matching ban exists.
        """
        return self._get(room_id, user_id) is not None

    def list_by_room(self, room_id: UUID) -> list[RoomBan]:
        """Retrieve all bans for a given room.

        Args:
            room_id: The room's unique identifier.

        Returns:
            List of RoomBan instances for the room.
        """
        statement = select(RoomBan).where(RoomBan.room_id == room_id)
        return list(self._session.exec(statement).all())

    def _get(self, room_id: UUID, user_id: UUID) -> RoomBan | None:
        """Fetch the ban row for a room/user pair, if any.

        Args:
            room_id: The room to look up.
            user_id: The user to look up.

        Returns:
            The RoomBan if present, None otherwise.
        """
        statement = select(RoomBan).where(
            RoomBan.room_id == room_id, RoomBan.user_id == user_id
        )
        return self._session.exec(statement).first()
