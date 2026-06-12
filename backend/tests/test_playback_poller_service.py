"""Tests for PlaybackPollerService."""

# ruff: noqa: D101, D102
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import httpx
import pytest

from backend.adapters.spotify_playback_adapter import SpotifyPlaybackState
from backend.db.models.enum import ItemStatus
from backend.services.playback_poller_service import PlaybackPollerService


class TestStartPolling:
    @pytest.fixture
    def poller(self):
        return PlaybackPollerService()

    def test_start_polling_creates_task(self, poller):
        room_id = uuid4()
        host_user_id = uuid4()

        async def _run():
            with patch.object(poller, "_poll_loop", new_callable=AsyncMock):
                await poller.start_polling(room_id, host_user_id)
                assert poller.is_polling(room_id)
                await poller.stop_all()

        anyio.run(_run)

    def test_start_polling_idempotent(self, poller):
        room_id = uuid4()
        host_user_id = uuid4()

        async def _run():
            with patch.object(poller, "_poll_loop", new_callable=AsyncMock):
                await poller.start_polling(room_id, host_user_id)
                await poller.start_polling(room_id, host_user_id)
                assert len(poller._active_tasks) == 1
                await poller.stop_all()

        anyio.run(_run)

    def test_is_polling_false_when_not_started(self, poller):
        assert not poller.is_polling(uuid4())


class TestStopPolling:
    @pytest.fixture
    def poller(self):
        return PlaybackPollerService()

    def test_stop_polling_cancels_task(self, poller):
        room_id = uuid4()
        host_user_id = uuid4()

        async def _run():
            with patch.object(poller, "_poll_loop", new_callable=AsyncMock):
                await poller.start_polling(room_id, host_user_id)
                assert poller.is_polling(room_id)
                await poller.stop_polling(room_id)
                assert not poller.is_polling(room_id)

        anyio.run(_run)

    def test_stop_polling_nonexistent_room_safe(self, poller):
        async def _run():
            await poller.stop_polling(uuid4())

        anyio.run(_run)

    def test_stop_all_clears_registry(self, poller):
        room_id_1 = uuid4()
        room_id_2 = uuid4()
        host_user_id = uuid4()

        async def _run():
            with patch.object(poller, "_poll_loop", new_callable=AsyncMock):
                await poller.start_polling(room_id_1, host_user_id)
                await poller.start_polling(room_id_2, host_user_id)
                assert len(poller._active_tasks) == 2
                await poller.stop_all()
                assert len(poller._active_tasks) == 0

        anyio.run(_run)


class TestPollLoopTrackChanged:
    @pytest.fixture
    def poller(self):
        return PlaybackPollerService()

    @patch("backend.services.playback_poller_service.SpotifyPlaybackAdapter")
    @patch("backend.services.playback_poller_service.settings")
    def test_track_mismatch_advances_when_next_in_queue(
        self, mock_settings, mock_adapter_cls
    ):
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0

        poller = PlaybackPollerService()
        room_id = uuid4()
        host_user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.current_song_id = "old_track"
        mock_session.playback_status = ItemStatus.PLAYING

        mock_next_item = MagicMock()
        mock_next_item.song.external_id = "new_track"

        call_count = 0

        def get_session_side_effect(rid):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return mock_session
            return None

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(
            return_value=SpotifyPlaybackState(
                is_playing=True,
                track_id="new_track",
                progress_ms=0,
                duration_ms=200000,
                device_id="device1",
            )
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            with (
                patch.object(
                    poller,
                    "_get_session_state",
                    side_effect=get_session_side_effect,
                ),
                patch.object(
                    poller,
                    "_get_valid_token",
                    new_callable=AsyncMock,
                    return_value="token",
                ),
                patch.object(
                    poller,
                    "_get_next_queue_item",
                    return_value=mock_next_item,
                ),
                patch.object(
                    poller,
                    "_advance_queue",
                    new_callable=AsyncMock,
                ) as mock_advance,
            ):
                await poller._poll_loop(room_id, host_user_id)

            mock_advance.assert_called_once_with(
                mock_session, room_id, host_user_id, mock_adapter
            )

        anyio.run(_run)

    @patch("backend.services.playback_poller_service.manager")
    @patch("backend.services.playback_poller_service.SpotifyPlaybackAdapter")
    @patch("backend.services.playback_poller_service.settings")
    def test_track_mismatch_adopts_external_track(
        self, mock_settings, mock_adapter_cls, mock_manager
    ):
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0
        mock_manager.broadcast = AsyncMock()

        poller = PlaybackPollerService()
        room_id = uuid4()
        host_user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.current_song_id = "old_track"
        mock_session.playback_status = ItemStatus.PLAYING

        call_count = 0

        def get_session_side_effect(rid):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return mock_session
            return None

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(
            return_value=SpotifyPlaybackState(
                is_playing=True,
                track_id="external_track",
                progress_ms=5000,
                duration_ms=200000,
                device_id="device1",
                track_name="External Song",
                track_artist="External Artist",
                album_art_url="https://example.com/art.jpg",
            )
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            with (
                patch.object(
                    poller,
                    "_get_session_state",
                    side_effect=get_session_side_effect,
                ),
                patch.object(
                    poller,
                    "_get_valid_token",
                    new_callable=AsyncMock,
                    return_value="token",
                ),
                patch.object(
                    poller,
                    "_get_next_queue_item",
                    return_value=None,
                ),
                patch.object(
                    poller,
                    "_get_current_queue_item",
                    return_value=None,
                ),
                patch.object(
                    poller,
                    "_adopt_external_track",
                ),
                patch.object(
                    poller,
                    "_advance_queue",
                    new_callable=AsyncMock,
                ) as mock_advance,
            ):
                await poller._poll_loop(room_id, host_user_id)

            mock_advance.assert_not_called()

        anyio.run(_run)


class TestPollLoopExternalPause:
    @patch("backend.services.playback_poller_service.SpotifyPlaybackAdapter")
    @patch("backend.services.playback_poller_service.settings")
    def test_external_pause_broadcasts(self, mock_settings, mock_adapter_cls):
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0

        poller = PlaybackPollerService()
        room_id = uuid4()
        host_user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.current_song_id = "track_123"
        mock_session.playback_status = ItemStatus.PLAYING

        call_count = 0

        def get_session_side_effect(rid):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return mock_session
            return None

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(
            return_value=SpotifyPlaybackState(
                is_playing=False,
                track_id="track_123",
                progress_ms=5000,
                duration_ms=200000,
                device_id="device1",
            )
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            with (
                patch.object(
                    poller,
                    "_get_session_state",
                    side_effect=get_session_side_effect,
                ),
                patch.object(
                    poller,
                    "_get_valid_token",
                    new_callable=AsyncMock,
                    return_value="token",
                ),
                patch.object(poller, "_update_session_status") as mock_update_status,
                patch.object(
                    poller,
                    "_broadcast_state_changed",
                    new_callable=AsyncMock,
                ) as mock_broadcast,
            ):
                await poller._poll_loop(room_id, host_user_id)

            mock_update_status.assert_called_once_with(session_id, ItemStatus.PAUSED)
            mock_broadcast.assert_called_once_with(room_id, "paused", "track_123")

        anyio.run(_run)

    @patch("backend.services.playback_poller_service.SpotifyPlaybackAdapter")
    @patch("backend.services.playback_poller_service.settings")
    def test_external_resume_broadcasts(self, mock_settings, mock_adapter_cls):
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0

        poller = PlaybackPollerService()
        room_id = uuid4()
        host_user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.current_song_id = "track_123"
        mock_session.playback_status = ItemStatus.PAUSED

        call_count = 0

        def get_session_side_effect(rid):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return mock_session
            return None

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(
            return_value=SpotifyPlaybackState(
                is_playing=True,
                track_id="track_123",
                progress_ms=5000,
                duration_ms=200000,
                device_id="device1",
            )
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            with (
                patch.object(
                    poller,
                    "_get_session_state",
                    side_effect=get_session_side_effect,
                ),
                patch.object(
                    poller,
                    "_get_valid_token",
                    new_callable=AsyncMock,
                    return_value="token",
                ),
                patch.object(poller, "_update_session_status") as mock_update_status,
                patch.object(
                    poller,
                    "_broadcast_state_changed",
                    new_callable=AsyncMock,
                ) as mock_broadcast,
            ):
                await poller._poll_loop(room_id, host_user_id)

            mock_update_status.assert_called_once_with(session_id, ItemStatus.PLAYING)
            mock_broadcast.assert_called_once_with(room_id, "playing", "track_123")

        anyio.run(_run)


class TestPollLoopNoDevice:
    @patch("backend.services.playback_poller_service.SpotifyPlaybackAdapter")
    @patch("backend.services.playback_poller_service.settings")
    def test_no_device_advances_queue(self, mock_settings, mock_adapter_cls):
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0

        poller = PlaybackPollerService()
        room_id = uuid4()
        host_user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.current_song_id = "track_123"
        mock_session.playback_status = ItemStatus.PLAYING

        call_count = 0

        def get_session_side_effect(rid):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return mock_session
            return None

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(return_value=None)
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            with (
                patch.object(
                    poller,
                    "_get_session_state",
                    side_effect=get_session_side_effect,
                ),
                patch.object(
                    poller,
                    "_get_valid_token",
                    new_callable=AsyncMock,
                    return_value="token",
                ),
                patch.object(
                    poller,
                    "_advance_queue",
                    new_callable=AsyncMock,
                ) as mock_advance,
            ):
                await poller._poll_loop(room_id, host_user_id)

            mock_advance.assert_called_once_with(
                mock_session, room_id, host_user_id, mock_adapter
            )

        anyio.run(_run)


class TestPollLoopRateLimit:
    @patch("backend.services.playback_poller_service.SpotifyPlaybackAdapter")
    @patch("backend.services.playback_poller_service.settings")
    def test_429_backs_off_with_retry_after(self, mock_settings, mock_adapter_cls):
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0

        poller = PlaybackPollerService()
        room_id = uuid4()
        host_user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.current_song_id = "track_123"
        mock_session.playback_status = ItemStatus.PLAYING

        call_count = 0

        def get_session_side_effect(rid):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return mock_session
            return None

        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {"Retry-After": "10"}

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "rate limited", request=MagicMock(), response=response_429
            )
        )
        mock_adapter_cls.return_value = mock_adapter

        sleep_values = []
        original_sleep = asyncio.sleep

        async def capture_sleep(duration):
            sleep_values.append(duration)
            await original_sleep(0)

        async def _run():
            with (
                patch.object(
                    poller,
                    "_get_session_state",
                    side_effect=get_session_side_effect,
                ),
                patch.object(
                    poller,
                    "_get_valid_token",
                    new_callable=AsyncMock,
                    return_value="token",
                ),
                patch("asyncio.sleep", side_effect=capture_sleep),
            ):
                await poller._poll_loop(room_id, host_user_id)

        anyio.run(_run)

        assert 10 in sleep_values


class TestPollLoopSelfStop:
    @patch("backend.services.playback_poller_service.settings")
    def test_session_deleted_stops_loop(self, mock_settings):
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0

        poller = PlaybackPollerService()
        room_id = uuid4()
        host_user_id = uuid4()

        async def _run():
            with patch.object(poller, "_get_session_state", return_value=None):
                await poller.start_polling(room_id, host_user_id)
                await asyncio.sleep(0.05)
                assert not poller.is_polling(room_id)

        anyio.run(_run)


class TestQueueOwnsCurrentTrack:
    def test_returns_true_when_external_id_matches(self):
        session = MagicMock()
        session.current_song_id = "abc"
        item = MagicMock()
        item.song.external_id = "abc"
        assert PlaybackPollerService._queue_owns_current_track(session, item) is True

    def test_returns_false_when_external_id_differs(self):
        session = MagicMock()
        session.current_song_id = "external_track"
        item = MagicMock()
        item.song.external_id = "queued_track"
        assert PlaybackPollerService._queue_owns_current_track(session, item) is False

    def test_returns_false_when_queue_item_is_none(self):
        session = MagicMock()
        session.current_song_id = "abc"
        assert PlaybackPollerService._queue_owns_current_track(session, None) is False

    def test_returns_false_when_session_has_no_current_song(self):
        session = MagicMock()
        session.current_song_id = None
        item = MagicMock()
        item.song.external_id = "abc"
        assert PlaybackPollerService._queue_owns_current_track(session, item) is False


class TestQueueItemSongEagerLoaded:
    """Guard against DetachedInstanceError when accessing item.song after
    the helper's DBSession closes. Without eager loading the poll loop
    silently swallows the error and the queue stalls."""

    def test_get_current_queue_item_song_accessible_after_session_close(self):
        from sqlmodel import Session as DBSession
        from sqlmodel import select

        from backend.db.database import engine
        from backend.db.models.queue_item import QueueItem

        with DBSession(engine) as s:
            row = s.exec(select(QueueItem).limit(1)).first()
            session_id = row.session_id if row else None

        if session_id is None:
            pytest.skip("no QueueItem rows in DB to exercise relation load")

        poller = PlaybackPollerService()
        item = poller._get_current_queue_item(session_id)
        assert item is not None
        # Must not raise DetachedInstanceError.
        assert item.song.external_id is not None

    def test_get_next_queue_item_song_accessible_after_session_close(self):
        from sqlmodel import Session as DBSession
        from sqlmodel import func, select

        from backend.db.database import engine
        from backend.db.models.queue_item import QueueItem

        with DBSession(engine) as s:
            stmt = (
                select(QueueItem.session_id)
                .group_by(QueueItem.session_id)
                .having(func.count(QueueItem.id) > 1)
                .limit(1)
            )
            session_id = s.exec(stmt).first()

        if session_id is None:
            pytest.skip("no session with >=2 QueueItems to exercise next item")

        poller = PlaybackPollerService()
        item = poller._get_next_queue_item(session_id)
        assert item is not None
        assert item.song.external_id is not None


class TestAdvanceQueueOwnership:
    def test_owned_advance_finishes_and_plays_next(self):
        poller = PlaybackPollerService()
        session = MagicMock()
        session.id = uuid4()
        session.current_song_id = "track_a"
        room_id = uuid4()
        host_user_id = uuid4()

        current_item = MagicMock()
        current_item.song.external_id = "track_a"
        next_item = MagicMock()
        next_item.song.external_id = "track_b"

        playback_service = MagicMock()
        playback_service.finish_song = AsyncMock()
        playback_service._broadcast_song_changed = AsyncMock()
        queue_service = MagicMock()
        queue_service.get_current_song = MagicMock(
            side_effect=[current_item, next_item]
        )

        adapter = AsyncMock()

        async def _run():
            with (
                patch.object(
                    poller,
                    "_build_playback_service_with_queue",
                    return_value=(playback_service, queue_service),
                ),
                patch.object(poller, "_update_session_track") as mock_update,
                patch.object(
                    poller, "_broadcast_state_changed", new_callable=AsyncMock
                ) as mock_state,
            ):
                await poller._advance_queue(session, room_id, host_user_id, adapter)

            playback_service.finish_song.assert_awaited_once_with(session.id)
            adapter.play.assert_awaited_once_with("spotify:track:track_b")
            mock_update.assert_called_once_with(
                session.id, "track_b", ItemStatus.PLAYING
            )
            mock_state.assert_awaited_once_with(room_id, "playing", "track_b")
            playback_service._broadcast_song_changed.assert_not_called()

        anyio.run(_run)

    def test_not_owned_advance_skips_finish_and_plays_first_item(self):
        poller = PlaybackPollerService()
        session = MagicMock()
        session.id = uuid4()
        session.current_song_id = "external_x"
        room_id = uuid4()
        host_user_id = uuid4()

        waiting_item = MagicMock()
        waiting_item.song.external_id = "queued_y"

        playback_service = MagicMock()
        playback_service.finish_song = AsyncMock()
        playback_service._broadcast_song_changed = AsyncMock()
        queue_service = MagicMock()
        queue_service.get_current_song = MagicMock(return_value=waiting_item)

        adapter = AsyncMock()

        async def _run():
            with (
                patch.object(
                    poller,
                    "_build_playback_service_with_queue",
                    return_value=(playback_service, queue_service),
                ),
                patch.object(poller, "_update_session_track") as mock_update,
                patch.object(
                    poller, "_broadcast_state_changed", new_callable=AsyncMock
                ) as mock_state,
            ):
                await poller._advance_queue(session, room_id, host_user_id, adapter)

            playback_service.finish_song.assert_not_called()
            adapter.play.assert_awaited_once_with("spotify:track:queued_y")
            mock_update.assert_called_once_with(
                session.id, "queued_y", ItemStatus.PLAYING
            )
            mock_state.assert_awaited_once_with(room_id, "playing", "queued_y")
            playback_service._broadcast_song_changed.assert_awaited_once_with(
                session.id, waiting_item.song
            )

        anyio.run(_run)

    def test_not_owned_advance_with_empty_queue_stops_playback(self):
        poller = PlaybackPollerService()
        session = MagicMock()
        session.id = uuid4()
        session.current_song_id = "external_x"
        room_id = uuid4()
        host_user_id = uuid4()

        playback_service = MagicMock()
        playback_service.finish_song = AsyncMock()
        playback_service._broadcast_song_changed = AsyncMock()
        queue_service = MagicMock()
        queue_service.get_current_song = MagicMock(return_value=None)

        adapter = AsyncMock()

        async def _run():
            with (
                patch.object(
                    poller,
                    "_build_playback_service_with_queue",
                    return_value=(playback_service, queue_service),
                ),
                patch.object(poller, "_update_session_status") as mock_status,
                patch.object(
                    poller, "_broadcast_state_changed", new_callable=AsyncMock
                ) as mock_state,
            ):
                await poller._advance_queue(session, room_id, host_user_id, adapter)

            playback_service.finish_song.assert_not_called()
            adapter.pause.assert_awaited_once()
            mock_status.assert_called_once_with(session.id, ItemStatus.STOPPED)
            mock_state.assert_awaited_once_with(room_id, "stopped")

        anyio.run(_run)


class TestPollLoopExternalEndsWithQueuedWaiting:
    @patch("backend.services.playback_poller_service.SpotifyPlaybackAdapter")
    @patch("backend.services.playback_poller_service.settings")
    def test_external_track_replaced_takes_control_of_queue(
        self, mock_settings, mock_adapter_cls
    ):
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0

        poller = PlaybackPollerService()
        room_id = uuid4()
        host_user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.current_song_id = "external_x"
        mock_session.playback_status = ItemStatus.PLAYING

        waiting_item = MagicMock()
        waiting_item.song.external_id = "queued_y"

        call_count = 0

        def get_session_side_effect(rid):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return mock_session
            return None

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(
            return_value=SpotifyPlaybackState(
                is_playing=True,
                track_id="external_z",
                progress_ms=1000,
                duration_ms=200000,
                device_id="device1",
            )
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            with (
                patch.object(
                    poller,
                    "_get_session_state",
                    side_effect=get_session_side_effect,
                ),
                patch.object(
                    poller,
                    "_get_valid_token",
                    new_callable=AsyncMock,
                    return_value="token",
                ),
                patch.object(poller, "_get_next_queue_item", return_value=None),
                patch.object(
                    poller, "_get_current_queue_item", return_value=waiting_item
                ),
                patch.object(poller, "_adopt_external_track") as mock_adopt,
                patch.object(
                    poller, "_advance_queue", new_callable=AsyncMock
                ) as mock_advance,
            ):
                await poller._poll_loop(room_id, host_user_id)

            mock_advance.assert_awaited_once_with(
                mock_session, room_id, host_user_id, mock_adapter
            )
            mock_adopt.assert_not_called()

        anyio.run(_run)


class TestPollLoopAutoplayOverridesQueue:
    @patch("backend.services.playback_poller_service.SpotifyPlaybackAdapter")
    @patch("backend.services.playback_poller_service.settings")
    def test_owned_song_ends_spotify_autoplay_unrelated_advances_to_next(
        self, mock_settings, mock_adapter_cls
    ):
        """Queue-owned A ends, Spotify autoplay starts off-queue Z, queue has B.

        Expect: take control with B (advance_queue), do NOT adopt Z. Otherwise
        B never plays — symptom user reported as "se añade a la cola pero
        cuando la canción termina no salta a la siguiente".
        """
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0

        poller = PlaybackPollerService()
        room_id = uuid4()
        host_user_id = uuid4()
        session_id = uuid4()

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.current_song_id = "queued_a"
        mock_session.playback_status = ItemStatus.PLAYING

        current_item = MagicMock()
        current_item.song.external_id = "queued_a"
        next_item = MagicMock()
        next_item.song.external_id = "queued_b"

        call_count = 0

        def get_session_side_effect(rid):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return mock_session
            return None

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(
            return_value=SpotifyPlaybackState(
                is_playing=True,
                track_id="autoplay_z",
                progress_ms=1000,
                duration_ms=200000,
                device_id="device1",
            )
        )
        mock_adapter_cls.return_value = mock_adapter

        async def _run():
            with (
                patch.object(
                    poller,
                    "_get_session_state",
                    side_effect=get_session_side_effect,
                ),
                patch.object(
                    poller,
                    "_get_valid_token",
                    new_callable=AsyncMock,
                    return_value="token",
                ),
                patch.object(poller, "_get_next_queue_item", return_value=next_item),
                patch.object(
                    poller, "_get_current_queue_item", return_value=current_item
                ),
                patch.object(poller, "_adopt_external_track") as mock_adopt,
                patch.object(
                    poller, "_advance_queue", new_callable=AsyncMock
                ) as mock_advance,
            ):
                await poller._poll_loop(room_id, host_user_id)

            mock_advance.assert_awaited_once_with(
                mock_session, room_id, host_user_id, mock_adapter
            )
            mock_adopt.assert_not_called()

        anyio.run(_run)
