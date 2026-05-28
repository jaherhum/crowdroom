"""Tests for QueueService."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest

from backend.core.exceptions import EntityNotFoundException
from backend.db.models.queue_item import QueueItem
from backend.repositories.queue_repo import QueueRepository
from backend.repositories.session_repo import SessionRepository
from backend.services.queue_service import QueueService


class TestQueueService:
    @pytest.fixture
    def mock_queue_repo(self):
        return MagicMock(spec=QueueRepository)

    @pytest.fixture
    def mock_session_repo(self):
        repo = MagicMock(spec=SessionRepository)
        session_obj = MagicMock()
        session_obj.room_id = uuid4()
        repo.get_by_id.return_value = session_obj
        return repo

    @pytest.fixture
    def queue_service(self, mock_queue_repo, mock_session_repo):
        return QueueService(mock_queue_repo, mock_session_repo)

    # -- add_to_queue --

    def test_add_to_queue_manual(self, queue_service, mock_queue_repo):
        session_id, song_id, user_id = uuid4(), uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item
        mock_queue_repo.get_all_by_session.return_value = []

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                return await queue_service.add_to_queue(
                    session_id, song_id, user_id, group="manual"
                )

        result = anyio.run(_run)

        assert result == mock_item
        mock_queue_repo.add_to_queue_atomic.assert_called_once_with(
            session_id, song_id, user_id, "manual"
        )

    def test_add_to_queue_playlist(self, queue_service, mock_queue_repo):
        session_id, song_id = uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item
        mock_queue_repo.get_all_by_session.return_value = []

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                await queue_service.add_to_queue(session_id, song_id, group="playlist")

        anyio.run(_run)

        mock_queue_repo.add_to_queue_atomic.assert_called_once_with(
            session_id, song_id, None, "playlist"
        )

    def test_add_to_queue_empty_group(self, queue_service, mock_queue_repo):
        session_id, song_id = uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item
        mock_queue_repo.get_all_by_session.return_value = []

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                await queue_service.add_to_queue(session_id, song_id, group="manual")

        anyio.run(_run)

        mock_queue_repo.add_to_queue_atomic.assert_called_once_with(
            session_id, song_id, None, "manual"
        )

    def test_add_to_queue_default_group(self, queue_service, mock_queue_repo):
        session_id, song_id = uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item
        mock_queue_repo.get_all_by_session.return_value = []

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                await queue_service.add_to_queue(session_id, song_id)

        anyio.run(_run)

        mock_queue_repo.add_to_queue_atomic.assert_called_once_with(
            session_id, song_id, None, "manual"
        )

    def test_add_to_queue_broadcasts_event(
        self, queue_service, mock_queue_repo, mock_session_repo
    ):
        session_id, song_id, user_id = uuid4(), uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_item.position = 1
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item
        mock_queue_repo.get_all_by_session.return_value = []
        mock_broadcast = AsyncMock()

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await queue_service.add_to_queue(
                    session_id, song_id, user_id, group="manual"
                )

        anyio.run(_run)

        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args[0]
        assert call_args[0]["type"] == "queue_updated"
        assert call_args[0]["action"] == "added"

    def test_add_to_queue_broadcasts_song_changed_for_first_song(
        self, queue_service, mock_queue_repo, mock_session_repo
    ):
        """add_to_queue broadcasts song_changed when item is at position 0."""
        session_id, song_id, user_id = uuid4(), uuid4(), uuid4()
        room_id = uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_item.position = 0
        mock_item.song = MagicMock()
        mock_item.song.id = song_id
        mock_item.song.external_id = "spotify:track:abc"
        mock_item.song.title = "First Song"
        mock_item.song.artist = "Artist"
        mock_item.song.platform = "spotify"
        mock_item.song.duration = 180.0
        mock_item.song.album_art_url = None
        mock_item.song.is_explicit = False
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item
        mock_queue_repo.get_all_by_session.return_value = []

        session_obj = MagicMock()
        session_obj.room_id = room_id
        mock_session_repo.get_by_id.return_value = session_obj

        mock_broadcast = AsyncMock()

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await queue_service.add_to_queue(
                    session_id, song_id, user_id, group="manual"
                )

        anyio.run(_run)

        assert mock_broadcast.call_count == 2
        first_call = mock_broadcast.call_args_list[0][0]
        assert first_call[0]["type"] == "queue_updated"
        second_call = mock_broadcast.call_args_list[1][0]
        assert second_call[0]["type"] == "song_changed"
        assert second_call[0]["song"] is not None
        assert second_call[1] == str(room_id)

    def test_add_to_queue_no_song_changed_when_not_first(
        self, queue_service, mock_queue_repo, mock_session_repo
    ):
        """add_to_queue does not broadcast song_changed when position > 0."""
        session_id, song_id, user_id = uuid4(), uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_item.position = 2
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item
        mock_queue_repo.get_all_by_session.return_value = []
        mock_broadcast = AsyncMock()

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await queue_service.add_to_queue(
                    session_id, song_id, user_id, group="manual"
                )

        anyio.run(_run)

        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args[0]
        assert call_args[0]["type"] == "queue_updated"

    # -- remove_from_queue --

    def test_remove_from_queue_success(self, queue_service, mock_queue_repo):
        item_id = uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_item.session_id = uuid4()
        mock_queue_repo.get_by_id.return_value = mock_item
        mock_queue_repo.delete.return_value = True
        mock_queue_repo.get_all_by_session.return_value = []

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                await queue_service.remove_from_queue(item_id)

        anyio.run(_run)

        mock_queue_repo.get_by_id.assert_called_once_with(item_id)
        mock_queue_repo.delete.assert_called_once_with(item_id)

    def test_remove_from_queue_not_found_lookup(self, queue_service, mock_queue_repo):
        """EntityNotFoundException raised by get_queue_item lookup."""
        item_id = uuid4()
        mock_queue_repo.get_by_id.return_value = None

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                await queue_service.remove_from_queue(item_id)

        with pytest.raises(EntityNotFoundException):
            anyio.run(_run)

    def test_remove_from_queue_delete_fails(self, queue_service, mock_queue_repo):
        """EntityNotFoundException raised when delete returns False."""
        item_id = uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_item.session_id = uuid4()
        mock_queue_repo.get_by_id.return_value = mock_item
        mock_queue_repo.delete.return_value = False

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                await queue_service.remove_from_queue(item_id)

        with pytest.raises(EntityNotFoundException):
            anyio.run(_run)

    def test_remove_from_queue_broadcasts_event(
        self, queue_service, mock_queue_repo, mock_session_repo
    ):
        item_id = uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_item.session_id = uuid4()
        mock_queue_repo.get_by_id.return_value = mock_item
        mock_queue_repo.delete.return_value = True
        mock_queue_repo.get_all_by_session.return_value = []
        mock_broadcast = AsyncMock()

        async def _run():
            with patch("backend.services.queue_service.manager") as mock_manager:
                mock_manager.broadcast = mock_broadcast
                await queue_service.remove_from_queue(item_id)

        anyio.run(_run)

        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args[0]
        assert call_args[0]["type"] == "queue_updated"
        assert call_args[0]["action"] == "removed"

    # -- get_queue_item --

    def test_get_queue_item_success(self, queue_service, mock_queue_repo):
        item_id = uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.get_by_id.return_value = mock_item

        result = queue_service.get_queue_item(item_id)

        assert result == mock_item
        mock_queue_repo.get_by_id.assert_called_once_with(item_id)

    def test_get_queue_item_not_found(self, queue_service, mock_queue_repo):
        item_id = uuid4()
        mock_queue_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            queue_service.get_queue_item(item_id)

    # -- get_queue --

    def test_get_queue(self, queue_service, mock_queue_repo):
        session_id = uuid4()
        mock_items = [MagicMock(spec=QueueItem), MagicMock(spec=QueueItem)]
        mock_queue_repo.get_all_by_session.return_value = mock_items

        result = queue_service.get_queue(session_id)

        assert result == mock_items
        mock_queue_repo.get_all_by_session.assert_called_once_with(session_id)

    # -- get_current_song --

    def test_get_current_song(self, queue_service, mock_queue_repo):
        session_id = uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.get_first_item.return_value = mock_item

        result = queue_service.get_current_song(session_id)

        assert result == mock_item
        mock_queue_repo.get_first_item.assert_called_once_with(session_id)

    def test_get_current_song_empty(self, queue_service, mock_queue_repo):
        session_id = uuid4()
        mock_queue_repo.get_first_item.return_value = None

        result = queue_service.get_current_song(session_id)

        assert result is None

    # -- get_queue_count --

    def test_get_queue_count(self, queue_service, mock_queue_repo):
        session_id = uuid4()
        mock_queue_repo.count_by_session.return_value = 5

        result = queue_service.get_queue_count(session_id)

        assert result == 5
        mock_queue_repo.count_by_session.assert_called_once_with(session_id)
