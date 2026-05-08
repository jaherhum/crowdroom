"""Tests for QueueHistoryService."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.db.models.queue_history import QueueHistory
from backend.repositories.queue_history_repo import QueueHistoryRepository
from backend.services.queue_history_service import QueueHistoryService


class TestQueueHistoryService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=QueueHistoryRepository)

    @pytest.fixture
    def service(self, mock_repo):
        return QueueHistoryService(mock_repo)

    # -- add_to_history --

    def test_add_to_history(self, service, mock_repo):
        session_id, song_id = uuid4(), uuid4()
        mock_entry = MagicMock(spec=QueueHistory)
        mock_repo.create.return_value = mock_entry

        result = service.add_to_history(session_id, song_id)

        assert result == mock_entry
        call_args = mock_repo.create.call_args[0][0]
        assert call_args.session_id == session_id
        assert call_args.song_id == song_id
        mock_repo.delete_oldest.assert_called_once_with(session_id, keep=15)

    # -- get_history --

    def test_get_history(self, service, mock_repo):
        session_id = uuid4()
        mock_entries = [MagicMock(spec=QueueHistory), MagicMock(spec=QueueHistory)]
        mock_repo.get_all_by_session.return_value = mock_entries

        result = service.get_history(session_id)

        assert result == mock_entries
        mock_repo.get_all_by_session.assert_called_once_with(session_id, limit=15)

    def test_get_history_custom_limit(self, service, mock_repo):
        session_id = uuid4()
        mock_repo.get_all_by_session.return_value = []

        service.get_history(session_id, limit=5)

        mock_repo.get_all_by_session.assert_called_once_with(session_id, limit=5)
