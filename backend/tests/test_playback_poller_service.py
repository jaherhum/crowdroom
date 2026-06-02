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
    def test_track_mismatch_calls_finish_song(self, mock_settings, mock_adapter_cls):
        mock_settings.PLAYBACK_POLL_INTERVAL_SECONDS = 0

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

        mock_playback_service = MagicMock()
        mock_playback_service.finish_song = AsyncMock(return_value="finished")

        mock_adapter = AsyncMock()
        mock_adapter.get_current_playback = AsyncMock(
            return_value=SpotifyPlaybackState(
                is_playing=True,
                track_id="new_track",
                progress_ms=0,
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
                    "_build_playback_service",
                    return_value=mock_playback_service,
                ),
                patch.object(poller, "_update_session_track") as mock_update_track,
            ):
                await poller._poll_loop(room_id, host_user_id)

            mock_playback_service.finish_song.assert_called_once_with(session_id)
            mock_update_track.assert_called_once_with(
                session_id, "new_track", ItemStatus.PLAYING
            )

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
    def test_no_device_marks_stopped(self, mock_settings, mock_adapter_cls):
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
                patch.object(poller, "_update_session_status") as mock_update_status,
                patch.object(
                    poller,
                    "_broadcast_state_changed",
                    new_callable=AsyncMock,
                ) as mock_broadcast,
            ):
                await poller._poll_loop(room_id, host_user_id)

            mock_update_status.assert_called_once_with(session_id, ItemStatus.STOPPED)
            mock_broadcast.assert_called_once_with(room_id, "stopped", "track_123")

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
