"""Tests for PlaybackService."""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.db.models.queue_history import QueueHistory
from backend.db.models.queue_item import QueueItem
from backend.repositories.queue_history_repo import QueueHistoryRepository
from backend.repositories.session_repo import SessionRepository
from backend.services.playback_service import MAX_HISTORY, PlaybackService
from backend.services.queue_service import QueueService


class TestPlaybackService:
    @pytest.fixture
    def mock_session_repo(self):
        return MagicMock(spec=SessionRepository)

    @pytest.fixture
    def mock_queue_service(self):
        return MagicMock(spec=QueueService)

    @pytest.fixture
    def mock_history_repo(self):
        return MagicMock(spec=QueueHistoryRepository)

    @pytest.fixture
    def playback_service(
        self, mock_session_repo, mock_queue_service, mock_history_repo
    ):
        return PlaybackService(mock_session_repo, mock_queue_service, mock_history_repo)

    # -- finish_song --

    def test_finish_records_history_and_removes(
        self, playback_service, mock_queue_service
    ):
        """finish_song marks item as FINISHED, records history, removes from queue."""
        session_id = uuid4()
        song_id = uuid4()
        current_item = MagicMock(spec=QueueItem)
        current_item.session_id = session_id
        current_item.song_id = song_id
        mock_queue_service.get_current_song.return_value = current_item

        result = playback_service.finish_song(session_id)

        assert result == "finished"
        assert current_item.playback_status.name == "FINISHED"
        playback_service._queue_history_repo.create.assert_called_once()
        mock_queue_service.remove_from_queue.assert_called_once_with(current_item.id)

    def test_finish_song_no_current_item(self, playback_service, mock_queue_service):
        """finish_song does nothing when there is no current song."""
        session_id = uuid4()
        mock_queue_service.get_current_song.return_value = None

        result = playback_service.finish_song(session_id)

        assert result == "finished"
        playback_service._queue_history_repo.create.assert_not_called()
        mock_queue_service.remove_from_queue.assert_not_called()

    def test_record_history_calls_create_and_prune(self, playback_service):
        """_record_history creates an entry and prunes old ones."""
        session_id = uuid4()
        song_id = uuid4()

        playback_service._record_history(session_id, song_id)

        history_repo = playback_service._queue_history_repo
        # Verify create was called with a QueueHistory
        # having the correct session and song
        create_call = history_repo.create.call_args
        assert create_call is not None
        actual_entry = create_call[0][0]
        assert actual_entry.session_id == session_id
        assert actual_entry.song_id == song_id
        history_repo.delete_oldest.assert_called_once_with(session_id, keep=MAX_HISTORY)


class TestQueueHistoryRepository:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_session):
        return QueueHistoryRepository(mock_session)

    # -- create --

    def test_create_records_history_entry(self, repo, mock_session):
        session_id, song_id = uuid4(), uuid4()
        history = QueueHistory(session_id=session_id, song_id=song_id)

        result = repo.create(history)

        mock_session.add.assert_called_once_with(history)
        mock_session.commit.assert_called_once()
        assert result.session_id == session_id
        assert result.song_id == song_id

    # -- get_by_session --

    def test_get_by_session_returns_newest_first(self, repo, mock_session):
        session_id = uuid4()
        now = datetime.now()
        newest = QueueHistory(session_id=session_id, song_id=uuid4(), played_at=now)
        oldest = QueueHistory(
            session_id=session_id, song_id=uuid4(), played_at=datetime(2025, 1, 1)
        )

        mock_exec = MagicMock()
        mock_exec.all.return_value = [newest, oldest]
        mock_session.exec.return_value = mock_exec

        result = repo.get_by_session(session_id)

        assert result == [newest, oldest]

    def test_get_by_session_respects_limit(self, repo, mock_session):
        session_id = uuid4()
        mock_exec = MagicMock()
        mock_exec.all.return_value = []
        mock_session.exec.return_value = mock_exec

        result = repo.get_by_session(session_id, limit=10)

        assert len(result) == 0

    # -- delete_oldest (FIFO eviction) --

    def test_delete_oldest_when_exceeds_limit(self, repo, mock_session):
        old_entry1 = QueueHistory(session_id=uuid4(), song_id=uuid4())
        old_entry2 = QueueHistory(session_id=old_entry1.session_id, song_id=uuid4())

        mock_exec = MagicMock()
        mock_exec.all.return_value = [old_entry1, old_entry2]
        mock_session.exec.return_value = mock_exec

        repo.delete_oldest(old_entry1.session_id, keep=1)

        mock_session.delete.assert_any_call(old_entry1)
        mock_session.delete.assert_any_call(old_entry2)
        mock_session.commit.assert_called_once()

    def test_delete_oldest_when_at_limit(self, repo, mock_session):
        session_id = uuid4()
        mock_exec = MagicMock()
        mock_exec.all.return_value = []
        mock_session.exec.return_value = mock_exec

        repo.delete_oldest(session_id, keep=15)

        mock_session.delete.assert_not_called()

    # -- count_by_session --

    def test_count_by_session(self, repo, mock_session):
        session_id = uuid4()
        mock_exec = MagicMock()
        mock_exec.one.return_value = 3
        mock_session.exec.return_value = mock_exec

        result = repo.count_by_session(session_id)

        assert result == 3
