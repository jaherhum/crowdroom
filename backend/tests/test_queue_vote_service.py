"""Tests for QueueVoteService."""

from unittest.mock import AsyncMock, MagicMock
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
    def service(self, mock_repo):
        return QueueVoteService(queue_vote_repo=mock_repo)

    # -- cast_vote --

    def test_cast_vote_success(self, service, mock_repo):
        item_id, user_id = uuid4(), uuid4()
        mock_repo.get_by_item_and_user.return_value = None
        mock_vote = MagicMock(spec=QueueVote)
        mock_repo.create.return_value = mock_vote

        async def _run():
            return await service.cast_vote(item_id, user_id)

        result = anyio.run(_run)

        assert result == mock_vote
        mock_repo.get_by_item_and_user.assert_called_once_with(item_id, user_id)
        call_args = mock_repo.create.call_args[0][0]
        assert call_args.queue_item_id == item_id
        assert call_args.user_id == user_id

    def test_cast_vote_duplicate(self, service, mock_repo):
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

    # -- _check_skip_threshold --

    def test_check_skip_threshold_defaults_to_two(self, mock_repo):
        mock_playback = MagicMock(spec=PlaybackService)
        mock_playback.finish_song = AsyncMock()
        service = QueueVoteService(
            queue_vote_repo=mock_repo, playback_service=mock_playback
        )

        mock_vote = MagicMock(spec=QueueVote)
        mock_vote.queue_item_id = uuid4()
        mock_session = MagicMock()
        mock_session.id = uuid4()
        mock_room = MagicMock()
        mock_room.settings = {}
        mock_session.room = mock_room
        mock_vote.queue_item.session = mock_session

        mock_repo.count_by_item.return_value = 1

        async def _run_below():
            await service._check_skip_threshold(mock_vote)

        anyio.run(_run_below)
        mock_playback.finish_song.assert_not_called()

        mock_repo.count_by_item.return_value = 2

        async def _run_at():
            await service._check_skip_threshold(mock_vote)

        anyio.run(_run_at)
        mock_playback.finish_song.assert_called_once_with(mock_session.id)

    def test_check_skip_threshold_uses_configured_value(self, mock_repo):
        mock_playback = MagicMock(spec=PlaybackService)
        mock_playback.finish_song = AsyncMock()
        service = QueueVoteService(
            queue_vote_repo=mock_repo, playback_service=mock_playback
        )

        mock_vote = MagicMock(spec=QueueVote)
        mock_vote.queue_item_id = uuid4()
        mock_session = MagicMock()
        mock_session.id = uuid4()
        mock_room = MagicMock()
        mock_room.settings = {"skip_threshold": 5}
        mock_session.room = mock_room
        mock_vote.queue_item.session = mock_session

        mock_repo.count_by_item.return_value = 4

        async def _run_below():
            await service._check_skip_threshold(mock_vote)

        anyio.run(_run_below)
        mock_playback.finish_song.assert_not_called()

        mock_repo.count_by_item.return_value = 5

        async def _run_at():
            await service._check_skip_threshold(mock_vote)

        anyio.run(_run_at)
        mock_playback.finish_song.assert_called_once_with(mock_session.id)
