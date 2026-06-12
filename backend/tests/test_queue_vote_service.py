"""Tests for QueueVoteService."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest

from backend.core.exceptions import EntityExistsException
from backend.db.models.queue_vote import QueueVote
from backend.repositories.queue_vote_repo import QueueVoteRepository
from backend.services.playback_service import PlaybackService
from backend.services.queue_vote_service import QueueVoteService


class TestQueueVoteService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=QueueVoteRepository)

    @pytest.fixture
    def mock_manager(self):
        with patch("backend.services.queue_vote_service.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            yield mock_mgr

    @pytest.fixture
    def service(self, mock_repo):
        return QueueVoteService(queue_vote_repo=mock_repo)

    # -- cast_vote --

    def test_cast_vote_success(self, service, mock_repo, mock_manager):
        item_id, user_id = uuid4(), uuid4()
        mock_repo.get_by_item_and_user.return_value = None
        mock_vote = MagicMock(spec=QueueVote)
        mock_vote.queue_item_id = item_id
        mock_vote.user_id = user_id
        mock_session = MagicMock()
        mock_session.id = uuid4()
        mock_room = MagicMock()
        mock_room.id = uuid4()
        mock_room.settings = {}
        mock_session.room = mock_room
        mock_vote.queue_item.session = mock_session
        mock_repo.create.return_value = mock_vote
        mock_repo.count_by_item.return_value = 1

        async def _run():
            return await service.cast_vote(item_id, user_id)

        result = anyio.run(_run)

        assert result == mock_vote
        mock_repo.get_by_item_and_user.assert_called_once_with(item_id, user_id)
        call_args = mock_repo.create.call_args[0][0]
        assert call_args.queue_item_id == item_id
        assert call_args.user_id == user_id

    def test_cast_vote_duplicate(self, service, mock_repo, mock_manager):
        item_id, user_id = uuid4(), uuid4()
        mock_repo.get_by_item_and_user.return_value = MagicMock(spec=QueueVote)

        async def _run():
            await service.cast_vote(item_id, user_id)

        with pytest.raises(EntityExistsException):
            anyio.run(_run)

        mock_repo.create.assert_not_called()

    # -- vote_count --

    def test_vote_count(self, service, mock_repo):
        item_id = uuid4()
        mock_repo.count_by_item.return_value = 3

        result = service.vote_count(item_id)

        assert result == 3
        mock_repo.count_by_item.assert_called_once_with(item_id)

    def test_vote_count_zero(self, service, mock_repo):
        item_id = uuid4()
        mock_repo.count_by_item.return_value = 0

        result = service.vote_count(item_id)

        assert result == 0


class TestSkipVoteBroadcast:
    """Tests for skip_vote WebSocket broadcast."""

    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=QueueVoteRepository)

    @pytest.fixture
    def mock_manager(self):
        with patch("backend.services.queue_vote_service.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            yield mock_mgr

    @pytest.fixture
    def mock_playback(self):
        mock_pb = MagicMock(spec=PlaybackService)
        mock_pb.finish_song = AsyncMock()
        return mock_pb

    @pytest.fixture
    def mock_vote_context(self):
        """Create a mock vote with full room chain."""
        item_id = uuid4()
        user_id = uuid4()
        room_id = uuid4()
        session_id = uuid4()

        mock_vote = MagicMock(spec=QueueVote)
        mock_vote.queue_item_id = item_id
        mock_vote.user_id = user_id

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_room = MagicMock()
        mock_room.id = room_id
        mock_room.settings = {"skip_threshold": 3}
        mock_session.room = mock_room
        mock_vote.queue_item.session = mock_session

        return mock_vote, room_id, session_id

    def test_broadcast_skip_vote_below_threshold(
        self, mock_repo, mock_manager, mock_playback, mock_vote_context
    ):
        mock_vote, room_id, session_id = mock_vote_context
        service = QueueVoteService(
            queue_vote_repo=mock_repo, playback_service=mock_playback
        )
        mock_repo.count_by_item.return_value = 1

        async def _run():
            await service._broadcast_and_check_skip(mock_vote)

        anyio.run(_run)

        mock_manager.broadcast.assert_called_once()
        payload = mock_manager.broadcast.call_args[0][0]
        assert payload["type"] == "skip_vote"
        assert payload["room_id"] == str(room_id)
        assert payload["queue_item_id"] == str(mock_vote.queue_item_id)
        assert payload["voter_id"] == str(mock_vote.user_id)
        assert payload["current_votes"] == 1
        assert payload["threshold"] == 3
        assert payload["skip_triggered"] is False
        mock_playback.finish_song.assert_not_called()

    def test_broadcast_skip_vote_threshold_reached(
        self, mock_repo, mock_manager, mock_playback, mock_vote_context
    ):
        mock_vote, room_id, session_id = mock_vote_context
        service = QueueVoteService(
            queue_vote_repo=mock_repo, playback_service=mock_playback
        )
        mock_repo.count_by_item.return_value = 3

        async def _run():
            await service._broadcast_and_check_skip(mock_vote)

        anyio.run(_run)

        payload = mock_manager.broadcast.call_args[0][0]
        assert payload["skip_triggered"] is True
        assert payload["current_votes"] == 3
        mock_playback.finish_song.assert_called_once_with(
            session_id, expected_item_id=mock_vote.queue_item_id
        )

    def test_broadcast_targets_correct_room(
        self, mock_repo, mock_manager, mock_playback, mock_vote_context
    ):
        mock_vote, room_id, _ = mock_vote_context
        service = QueueVoteService(
            queue_vote_repo=mock_repo, playback_service=mock_playback
        )
        mock_repo.count_by_item.return_value = 1

        async def _run():
            await service._broadcast_and_check_skip(mock_vote)

        anyio.run(_run)

        broadcast_room_id = mock_manager.broadcast.call_args[0][1]
        assert broadcast_room_id == str(room_id)

    def test_broadcast_default_threshold_two(self, mock_repo, mock_manager):
        service = QueueVoteService(queue_vote_repo=mock_repo)

        mock_vote = MagicMock(spec=QueueVote)
        mock_vote.queue_item_id = uuid4()
        mock_vote.user_id = uuid4()
        mock_session = MagicMock()
        mock_session.id = uuid4()
        mock_room = MagicMock()
        mock_room.id = uuid4()
        mock_room.settings = {}
        mock_session.room = mock_room
        mock_vote.queue_item.session = mock_session
        mock_repo.count_by_item.return_value = 2

        async def _run():
            await service._broadcast_and_check_skip(mock_vote)

        anyio.run(_run)

        payload = mock_manager.broadcast.call_args[0][0]
        assert payload["threshold"] == 2
        assert payload["skip_triggered"] is True

    def test_no_broadcast_when_session_missing(self, mock_repo, mock_manager):
        service = QueueVoteService(queue_vote_repo=mock_repo)

        mock_vote = MagicMock(spec=QueueVote)
        mock_vote.queue_item.session = None

        async def _run():
            await service._broadcast_and_check_skip(mock_vote)

        anyio.run(_run)

        mock_manager.broadcast.assert_not_called()

    def test_no_broadcast_when_room_missing(self, mock_repo, mock_manager):
        service = QueueVoteService(queue_vote_repo=mock_repo)

        mock_vote = MagicMock(spec=QueueVote)
        mock_session = MagicMock()
        mock_session.room = None
        mock_vote.queue_item.session = mock_session

        async def _run():
            await service._broadcast_and_check_skip(mock_vote)

        anyio.run(_run)

        mock_manager.broadcast.assert_not_called()

    def test_skip_triggered_without_playback_service(
        self, mock_repo, mock_manager, mock_vote_context
    ):
        """Skip triggered but no playback service — broadcast still sent."""
        mock_vote, room_id, _ = mock_vote_context
        service = QueueVoteService(queue_vote_repo=mock_repo)
        mock_repo.count_by_item.return_value = 3

        async def _run():
            await service._broadcast_and_check_skip(mock_vote)

        anyio.run(_run)

        payload = mock_manager.broadcast.call_args[0][0]
        assert payload["skip_triggered"] is True
