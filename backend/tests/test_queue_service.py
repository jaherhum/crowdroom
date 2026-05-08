"""Tests for QueueService."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.core.exceptions import EntityNotFoundException
from backend.db.models.queue_item import QueueItem
from backend.repositories.queue_repo import QueueRepository
from backend.services.queue_service import QueueService


class TestQueueService:
    @pytest.fixture
    def mock_queue_repo(self):
        return MagicMock(spec=QueueRepository)

    @pytest.fixture
    def queue_service(self, mock_queue_repo):
        return QueueService(mock_queue_repo)

    # -- add_to_queue --

    def test_add_to_queue_manual(self, queue_service, mock_queue_repo):
        session_id, song_id, user_id = uuid4(), uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item

        result = queue_service.add_to_queue(
            session_id, song_id, user_id, group="manual"
        )

        assert result == mock_item
        mock_queue_repo.add_to_queue_atomic.assert_called_once_with(
            session_id, song_id, user_id, "manual"
        )

    def test_add_to_queue_playlist(self, queue_service, mock_queue_repo):
        session_id, song_id = uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item

        queue_service.add_to_queue(session_id, song_id, group="playlist")

        mock_queue_repo.add_to_queue_atomic.assert_called_once_with(
            session_id, song_id, None, "playlist"
        )

    def test_add_to_queue_empty_group(self, queue_service, mock_queue_repo):
        session_id, song_id = uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item

        queue_service.add_to_queue(session_id, song_id, group="manual")

        mock_queue_repo.add_to_queue_atomic.assert_called_once_with(
            session_id, song_id, None, "manual"
        )

    def test_add_to_queue_default_group(self, queue_service, mock_queue_repo):
        session_id, song_id = uuid4(), uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.add_to_queue_atomic.return_value = mock_item

        queue_service.add_to_queue(session_id, song_id)

        mock_queue_repo.add_to_queue_atomic.assert_called_once_with(
            session_id, song_id, None, "manual"
        )

    # -- remove_from_queue --

    def test_remove_from_queue_success(self, queue_service, mock_queue_repo):
        item_id = uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.get_by_id.return_value = mock_item
        mock_queue_repo.delete.return_value = True

        queue_service.remove_from_queue(item_id)

        mock_queue_repo.get_by_id.assert_called_once_with(item_id)
        mock_queue_repo.delete.assert_called_once_with(item_id)

    def test_remove_from_queue_not_found_lookup(self, queue_service, mock_queue_repo):
        """EntityNotFoundException raised by get_queue_item lookup."""
        item_id = uuid4()
        mock_queue_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundException):
            queue_service.remove_from_queue(item_id)

    def test_remove_from_queue_delete_fails(self, queue_service, mock_queue_repo):
        """EntityNotFoundException raised when delete returns False."""
        item_id = uuid4()
        mock_item = MagicMock(spec=QueueItem)
        mock_queue_repo.get_by_id.return_value = mock_item
        mock_queue_repo.delete.return_value = False

        with pytest.raises(EntityNotFoundException):
            queue_service.remove_from_queue(item_id)

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
