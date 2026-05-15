"""Repository for Song data access."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DBSession
from sqlmodel import select

from backend.db.models.song import Song


class SongRepository:
    """Handles database operations for Songs."""

    def __init__(self, session: DBSession):
        """Initialize the SongRepository with a database session.

        Args:
            session: Database session for all CRUD operations on songs.
        """
        self._session = session

    def create(self, song: Song) -> Song:
        """Creates a new song in the database.

        Args:
            song (Song): The song instance to create.

        Returns:
            Song: The created song.

        Raises:
            IntegrityError: If a unique constraint is violated.
        """
        try:
            self._session.add(song)
            self._session.commit()
            self._session.refresh(song)
            return song
        except IntegrityError:
            self._session.rollback()
            raise

    def get_by_id(self, song_id: UUID) -> Song | None:
        """Retrieves a song by its ID.

        Args:
            song_id (UUID): The unique identifier of the song.

        Returns:
            Song | None: The song instance if found, otherwise None.
        """
        return self._session.get(Song, song_id)

    def get_by_external_id(self, external_id: str, platform: str) -> Song | None:
        """Retrieves a song by its external ID and platform.

        Args:
            external_id (str): The unique identifier from the streaming platform.
            platform (str): The streaming platform name.

        Returns:
            Song | None: The song instance if found, otherwise None.
        """
        return self._session.exec(
            select(Song).where(
                Song.external_id == external_id, Song.platform == platform
            )
        ).first()

    def get_all(self) -> list[Song]:
        """Retrieves all songs in the database.

        Returns:
            list[Song]: A list of all songs.
        """
        return list(self._session.exec(select(Song)).all())

    def update(self, song_id: UUID, update_data: dict) -> Song | None:
        """Updates an existing song with the provided data.

        Args:
            song_id (UUID): The unique identifier of the song.
            update_data (dict): A dictionary containing the fields to update.

        Returns:
            Song | None: The updated song instance if found, otherwise None.

        Raises:
            IntegrityError: If a unique constraint is violated.
        """
        song = self._session.get(Song, song_id)
        if song:
            for key, value in update_data.items():
                if hasattr(song, key):
                    setattr(song, key, value)
            try:
                self._session.add(song)
                self._session.commit()
                self._session.refresh(song)
                return song
            except IntegrityError:
                self._session.rollback()
                raise
        return None

    def delete(self, song_id: UUID) -> None:
        """Deletes a song from the database.

        Args:
            song_id (UUID): The unique identifier of the song to delete.
        """
        song = self._session.get(Song, song_id)
        if song:
            try:
                self._session.delete(song)
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise
