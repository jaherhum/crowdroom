"""Service for managing songs and their metadata."""

from uuid import UUID

from backend.core.exceptions import EntityExistsException, EntityNotFoundException
from backend.db.models.song import Song
from backend.repositories.song_repo import SongRepository
from backend.schemas.song import CreateSong, UpdateSong


class SongService:
    """Service for managing songs and their metadata."""

    def __init__(self, song_repo: SongRepository) -> None:
        """Initialize the SongService with a song repository.

        Args:
            song_repo (SongRepository): Repository for song operations.
        """
        self._song_repo = song_repo

    def get_song(self, song_id: UUID) -> Song:
        """Retrieve a specific song by its ID.

        Args:
            song_id (UUID): The unique identifier of the song.

        Returns:
            Song: The song instance.

        Raises:
            EntityNotFoundException: If the song is not found.
        """
        song = self._song_repo.get_by_id(song_id)
        if not song:
            raise EntityNotFoundException("Song", song_id)
        return song

    def get_all_songs(self) -> list[Song]:
        """Retrieve all songs.

        Returns:
            list[Song]: A list of all songs.
        """
        return self._song_repo.get_all()

    def get_by_external_id(self, external_id: str, platform: str) -> Song | None:
        """Retrieve a song by its external platform ID.

        Args:
            external_id: The platform-specific track identifier.
            platform: The streaming platform name.

        Returns:
            Song if found, None otherwise.
        """
        return self._song_repo.get_by_external_id(external_id, platform)

    def get_or_create_song(self, song_data: CreateSong) -> Song:
        """Retrieve an existing song or create a new one.

        Checks if a song with the same external_id and platform already exists.
        If it does, returns the existing song. Otherwise, creates a new one.

        Args:
            song_data (CreateSong): The schema containing song details.

        Returns:
            Song: The existing or newly created song.
        """
        existing = self._song_repo.get_by_external_id(
            song_data.external_id, song_data.platform.value
        )
        if existing:
            return existing

        new_song = Song(
            external_id=song_data.external_id,
            title=song_data.title,
            artist=song_data.artist,
            platform=song_data.platform,
            duration=song_data.duration,
            album_art_url=song_data.album_art_url,
            is_explicit=song_data.is_explicit,
        )
        return self._song_repo.create(new_song)

    def create_song(self, song_data: CreateSong) -> Song:
        """Create a new song.

        Args:
            song_data (CreateSong): The schema containing song details.

        Returns:
            Song: The newly created song.

        Raises:
            EntityExistsException: If the song already exists.
        """
        existing = self._song_repo.get_by_external_id(
            song_data.external_id, song_data.platform.value
        )
        if existing:
            raise EntityExistsException("Song")

        new_song = Song(
            external_id=song_data.external_id,
            title=song_data.title,
            artist=song_data.artist,
            platform=song_data.platform,
            duration=song_data.duration,
            album_art_url=song_data.album_art_url,
            is_explicit=song_data.is_explicit,
        )
        return self._song_repo.create(new_song)

    def update_song(self, song_id: UUID, song_data: UpdateSong) -> Song:
        """Update an existing song.

        Args:
            song_id (UUID): The unique identifier of the song to update.
            song_data (UpdateSong): The schema containing update details.

        Returns:
            Song: The updated song instance.

        Raises:
            EntityNotFoundException: If the song is not found.
        """
        self.get_song(song_id)
        update_data = song_data.model_dump(exclude_unset=True)
        updated_song = self._song_repo.update(song_id, update_data)
        if not updated_song:
            raise EntityNotFoundException("Song", song_id)
        return updated_song

    def delete_song(self, song_id: UUID) -> None:
        """Delete a song from the system.

        Args:
            song_id (UUID): The unique identifier of the song to delete.

        Raises:
            EntityNotFoundException: If the song is not found.
        """
        self.get_song(song_id)
        self._song_repo.delete(song_id)
