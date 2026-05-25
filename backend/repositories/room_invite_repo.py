"""Repository for RoomInvite data access."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import select

from backend.db.models.room_invite import RoomInvite


class RoomInviteRepository:
    """Handles database operations for RoomInvites."""

    def __init__(self, session: DBSession):
        """Initialize the RoomInviteRepository with a database session.

        Args:
            session: Database session for all CRUD operations on room invites.
        """
        self._session = session

    def create(self, invite: RoomInvite) -> RoomInvite:
        """Creates a new room invite in the database.

        Args:
            invite: The RoomInvite instance to create.

        Returns:
            The created RoomInvite, refreshed from the database.

        Raises:
            IntegrityError: If a unique constraint is violated (duplicate token).
        """
        try:
            self._session.add(invite)
            self._session.commit()
            self._session.refresh(invite)
            return invite
        except IntegrityError:
            self._session.rollback()
            raise

    def get_by_id(self, invite_id: UUID) -> RoomInvite | None:
        """Retrieves a room invite by its ID.

        Args:
            invite_id: The unique identifier of the invite.

        Returns:
            The RoomInvite if found, None otherwise.
        """
        return self._session.get(RoomInvite, invite_id)

    def get_by_token(self, token: str) -> RoomInvite | None:
        """Retrieves a room invite by its token.

        Args:
            token: The unique invite token string.

        Returns:
            The RoomInvite if found, None otherwise.
        """
        statement = select(RoomInvite).where(RoomInvite.token == token)
        return self._session.exec(statement).first()

    def get_by_room(self, room_id: UUID) -> list[RoomInvite]:
        """Retrieves all invites for a given room.

        Args:
            room_id: The room's unique identifier.

        Returns:
            List of RoomInvite instances for the room.
        """
        statement = select(RoomInvite).where(RoomInvite.room_id == room_id)
        return list(self._session.exec(statement).all())

    def increment_use_count(self, invite: RoomInvite) -> RoomInvite:
        """Atomically increments the use count of an invite.

        Args:
            invite: The RoomInvite to increment.

        Returns:
            The updated RoomInvite, refreshed from the database.
        """
        invite.use_count += 1
        self._session.add(invite)
        self._session.commit()
        self._session.refresh(invite)
        return invite

    def delete(self, invite_id: UUID) -> None:
        """Deletes a room invite by its ID.

        Args:
            invite_id: The unique identifier of the invite to delete.

        Raises:
            IntegrityError: If deletion violates a constraint.
        """
        invite = self._session.get(RoomInvite, invite_id)
        if invite:
            try:
                self._session.delete(invite)
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise
