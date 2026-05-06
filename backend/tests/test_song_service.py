"""Tests for SongService logic."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.core.exceptions import EntityExistsException, EntityNotFoundException
from backend.db.models.enum import StreamingPlatforms
from backend.db.models.song import Song
from backend.repositories.song_repo import SongRepository
from backend.schemas.song import CreateSong, UpdateSong
from backend.services.song_service import SongService


class TestSongService:
    """Tests for SongService logic."""

    @pytest.fixture
    def mock_song_repo(self):
        """Provides a mock SongRepository."""
        return MagicMock(spec=SongRepository)

    @pytest.fixture
    def song_service(self, mock_song_repo):
        """Provides a SongService instance with mocked repository."""
        return SongService(mock_song_repo)

    def test_get_song_success(self, song_service, mock_song_repo):
        """Test successful song retrieval."""
        song_id = uuid4()
        expected_song = MagicMock(spec=Song)
        mock_song_repo.get_by_id.return_value = expected_song

        result = song_service.get_song(song_id)

        assert result == expected_song
        mock_song_repo.get_by_id.assert_called_once_with(song_id)

    def test_get_song_not_found(self, song_service, mock_song_repo):
        """Test song retrieval when song does not exist."""
        song_id = uuid4()
        mock_song_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            song_service.get_song(song_id)

    def test_get_all_songs(self, song_service, mock_song_repo):
        """Test successful retrieval of all songs."""
        expected_songs = [MagicMock(spec=Song), MagicMock(spec=Song)]
        mock_song_repo.get_all.return_value = expected_songs

        result = song_service.get_all_songs()

        assert result == expected_songs
        mock_song_repo.get_all.assert_called_once()

    @patch("backend.services.song_service.Song")
    def test_create_song_success(
        self, mock_song_cls, song_service, mock_song_repo
    ):
        """Test successful song creation."""
        song_data = CreateSong(
            external_id="ext123",
            title="Test Song",
            artist="Test Artist",
            platform=StreamingPlatforms.SPOTIFY,
            duration=180.5,
        )
        mock_song = MagicMock(spec=Song)
        mock_song_cls.return_value = mock_song
        mock_song_repo.create.return_value = mock_song
        mock_song_repo.get_by_external_id.return_value = None

        result = song_service.create_song(song_data)

        assert result == mock_song
        mock_song_repo.create.assert_called_once()

    def test_create_song_already_exists(self, song_service, mock_song_repo):
        """Test song creation when song already exists."""
        song_data = CreateSong(
            external_id="ext123",
            title="Test Song",
            artist="Test Artist",
            platform=StreamingPlatforms.SPOTIFY,
            duration=180.5,
        )
        mock_song_repo.get_by_external_id.return_value = MagicMock(spec=Song)

        with pytest.raises(EntityExistsException):
            song_service.create_song(song_data)

    def test_update_song_success(self, song_service, mock_song_repo):
        """Test successful song update."""
        song_id = uuid4()
        existing_song = MagicMock(spec=Song)
        updated_song = MagicMock(spec=Song)
        update_data = UpdateSong(title="New Title")

        mock_song_repo.get_by_id.return_value = existing_song
        mock_song_repo.update.return_value = updated_song

        result = song_service.update_song(song_id, update_data)

        assert result == updated_song
        mock_song_repo.update.assert_called_once()

    def test_update_song_not_found(self, song_service, mock_song_repo):
        """Test song update when song does not exist."""
        song_id = uuid4()
        mock_song_repo.get_by_id.return_value = None
        update_data = UpdateSong(title="New Title")

        with pytest.raises(EntityNotFoundException):
            song_service.update_song(song_id, update_data)

    def test_delete_song_success(self, song_service, mock_song_repo):
        """Test successful song deletion."""
        song_id = uuid4()
        mock_song_repo.get_by_id.return_value = MagicMock(spec=Song)

        song_service.delete_song(song_id)

        mock_song_repo.delete.assert_called_once_with(song_id)

    def test_delete_song_not_found(self, song_service, mock_song_repo):
        """Test song deletion when song does not exist."""
        song_id = uuid4()
        mock_song_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            song_service.delete_song(song_id)

    def test_get_or_create_song_existing(self, song_service, mock_song_repo):
        """Test get_or_create returns existing song."""
        song_data = CreateSong(
            external_id="ext123",
            title="Test Song",
            artist="Test Artist",
            platform=StreamingPlatforms.SPOTIFY,
            duration=180.5,
        )
        existing_song = MagicMock(spec=Song)
        mock_song_repo.get_by_external_id.return_value = existing_song

        result = song_service.get_or_create_song(song_data)

        assert result == existing_song
        mock_song_repo.create.assert_not_called()

    @patch("backend.services.song_service.Song")
    def test_get_or_create_song_new(
        self, mock_song_cls, song_service, mock_song_repo
    ):
        """Test get_or_create creates new song when not found."""
        song_data = CreateSong(
            external_id="ext123",
            title="Test Song",
            artist="Test Artist",
            platform=StreamingPlatforms.SPOTIFY,
            duration=180.5,
        )
        mock_song = MagicMock(spec=Song)
        mock_song_cls.return_value = mock_song
        mock_song_repo.get_by_external_id.return_value = None
        mock_song_repo.create.return_value = mock_song

        result = song_service.get_or_create_song(song_data)

        assert result == mock_song
        mock_song_repo.create.assert_called_once()
