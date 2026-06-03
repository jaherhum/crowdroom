"""Background polling service for detecting external Spotify playback changes."""

import asyncio
import logging
from uuid import UUID

import httpx
from sqlmodel import Session as DBSession

from backend.adapters.spotify_playback_adapter import (
    SpotifyPlaybackAdapter,
    SpotifyPlaybackState,
)
from backend.api.websocket import manager
from backend.core.config import settings
from backend.db.database import engine
from backend.db.models.enum import ItemStatus, StreamingPlatforms
from backend.repositories.platform_connection_repo import PlatformConnectionRepo
from backend.repositories.queue_history_repo import QueueHistoryRepository
from backend.repositories.queue_repo import QueueRepository
from backend.repositories.session_repo import SessionRepository
from backend.services.platform_connection_service import PlatformConnectionService
from backend.services.playback_service import PlaybackService
from backend.services.queue_service import QueueService

logger = logging.getLogger(__name__)


class PlaybackPollerService:
    """Manages per-room background tasks that poll Spotify and reconcile state."""

    def __init__(self) -> None:
        self._active_tasks: dict[UUID, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def _get_session_state(self, room_id: UUID):
        """Read the current session for a room from a fresh DB connection.

        Args:
            room_id: The room whose session to look up.

        Returns:
            The Session model instance, or None if no session exists.
        """
        with DBSession(engine) as db_session:
            repo = SessionRepository(db_session)
            return repo.get_by_room(room_id)

    def _update_session_status(self, session_id: UUID, status: ItemStatus) -> None:
        """Update a session's playback_status in a fresh DB connection.

        Args:
            session_id: The session to update.
            status: The new playback status.
        """
        with DBSession(engine) as db_session:
            repo = SessionRepository(db_session)
            repo.update(session_id, {"playback_status": status})

    def _update_session_track(
        self, session_id: UUID, track_id: str, status: ItemStatus
    ) -> None:
        """Update a session's current track, status, and timing.

        Args:
            session_id: The session to update.
            track_id: The new Spotify track ID.
            status: The new playback status.
        """
        from datetime import datetime, timezone

        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        with DBSession(engine) as db_session:
            repo = SessionRepository(db_session)
            repo.update(
                session_id,
                {
                    "current_song_id": track_id,
                    "playback_status": status,
                    "playback_started_at": now_naive,
                    "playback_position_ms": 0,
                },
            )

    async def _get_valid_token(self, host_user_id: UUID) -> str:
        """Get a valid Spotify access token for the host user.

        Opens a fresh DB connection, builds PlatformConnectionService,
        and calls get_valid_access_token (which handles refresh if needed).

        Args:
            host_user_id: The host user whose token to retrieve.

        Returns:
            A valid Spotify access token string.
        """
        with DBSession(engine) as db_session:
            repo = PlatformConnectionRepo(db_session)
            service = PlatformConnectionService(repo)
            return await service.get_valid_access_token(
                host_user_id, StreamingPlatforms.SPOTIFY
            )

    def _build_playback_service_with_queue(
        self,
    ) -> tuple[PlaybackService, QueueService]:
        """Build PlaybackService and QueueService sharing same DB session.

        Returns:
            Tuple of (PlaybackService, QueueService) on same connection.
        """
        db_session = DBSession(engine)
        session_repo = SessionRepository(db_session)
        queue_repo = QueueRepository(db_session)
        queue_history_repo = QueueHistoryRepository(db_session)
        queue_service = QueueService(queue_repo)
        playback_service = PlaybackService(
            session_repo, queue_service, queue_history_repo
        )
        return playback_service, queue_service

    @staticmethod
    def _is_song_ended(state: SpotifyPlaybackState) -> bool:
        """Determine if Spotify stopped because the song finished.

        Spotify resets progress_ms to 0 after a single-URI track finishes,
        so we also treat progress_ms==0 with is_playing==False as ended.

        Args:
            state: Current playback state from Spotify.

        Returns:
            True if song appears to have finished playing.
        """
        if not state.duration_ms or state.progress_ms is None:
            return True
        if state.progress_ms == 0 and not state.is_playing:
            return True
        remaining = state.duration_ms - state.progress_ms
        return remaining < 5000

    async def _advance_queue(
        self,
        session,
        room_id: UUID,
        host_user_id: UUID,
        adapter: SpotifyPlaybackAdapter,
    ) -> None:
        """Finish current song and play CrowdRoom's next queue item.

        Args:
            session: The current session object.
            room_id: Room being managed.
            host_user_id: Host whose Spotify to control.
            adapter: Already-authenticated Spotify adapter.
        """
        playback_service, queue_service = self._build_playback_service_with_queue()
        await playback_service.finish_song(session.id)

        next_item = queue_service.get_current_song(session.id)
        next_uri = (
            f"spotify:track:{next_item.song.external_id}"
            if next_item and next_item.song
            else None
        )
        logger.info(
            "Room %s: advance_queue next_uri=%s", room_id, next_uri
        )

        if next_uri:
            try:
                await adapter.play(next_uri)
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 401:
                    try:
                        token = await self._get_valid_token(host_user_id)
                        adapter = SpotifyPlaybackAdapter(token)
                        await adapter.play(next_uri)
                    except httpx.HTTPStatusError:
                        logger.warning(
                            "Failed to auto-play next track for room %s "
                            "after token refresh",
                            room_id,
                        )
                        return
                else:
                    logger.warning(
                        "Failed to auto-play next track for room %s: %d",
                        room_id,
                        error.response.status_code,
                    )
                    return
            track_id = next_uri.split(":")[-1]
            await asyncio.to_thread(
                self._update_session_track,
                session.id,
                track_id,
                ItemStatus.PLAYING,
            )
            await self._broadcast_state_changed(room_id, "playing", track_id)
        else:
            try:
                await adapter.pause()
            except httpx.HTTPStatusError:
                pass
            await asyncio.to_thread(
                self._update_session_status, session.id, ItemStatus.STOPPED
            )
            await self._broadcast_state_changed(room_id, "stopped")

    async def _broadcast_state_changed(
        self, room_id: UUID, status: str, track_id: str | None = None
    ) -> None:
        """Broadcast a playback_state_changed event to all room members.

        Args:
            room_id: Room whose members should receive the event.
            status: New status string ('playing', 'paused', 'stopped').
            track_id: Spotify track ID, if any.
        """
        await manager.broadcast(
            {
                "type": "playback_state_changed",
                "room_id": str(room_id),
                "status": status,
                "track_id": track_id,
            },
            str(room_id),
        )

    async def start_polling(self, room_id: UUID, host_user_id: UUID) -> None:
        """Start a polling task for a room if one is not already running.

        Args:
            room_id: The room to poll for.
            host_user_id: The host whose Spotify token to use.
        """
        logger.info("start_polling called for room %s", room_id)
        async with self._lock:
            if room_id in self._active_tasks:
                return
            task = asyncio.create_task(self._poll_loop(room_id, host_user_id))
            self._active_tasks[room_id] = task

    async def stop_polling(self, room_id: UUID) -> None:
        """Cancel and clean up the polling task for a room.

        Args:
            room_id: The room whose poller to stop.
        """
        async with self._lock:
            task = self._active_tasks.pop(room_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def stop_all(self) -> None:
        """Cancel all active polling tasks. Called during app shutdown."""
        async with self._lock:
            tasks = list(self._active_tasks.values())
            self._active_tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def is_polling(self, room_id: UUID) -> bool:
        """Check whether a room currently has an active polling task."""
        return room_id in self._active_tasks

    async def _poll_loop(self, room_id: UUID, host_user_id: UUID) -> None:
        """Poll Spotify playback state and reconcile with internal queue.

        Args:
            room_id: The room being monitored.
            host_user_id: The host whose Spotify account to poll.
        """
        backoff = settings.PLAYBACK_POLL_INTERVAL_SECONDS
        max_backoff = 30
        logger.info("Poll loop started for room %s (every %ds)", room_id, backoff)

        try:
            while True:
                await asyncio.sleep(backoff)

                try:
                    session = await asyncio.to_thread(self._get_session_state, room_id)
                    if not session:
                        break

                    token = await self._get_valid_token(host_user_id)
                    adapter = SpotifyPlaybackAdapter(token)
                    state = await adapter.get_current_playback()

                    logger.info(
                        "Poll room %s: state=%s, session_status=%s, "
                        "session_track=%s",
                        room_id,
                        state,
                        session.playback_status,
                        session.current_song_id,
                    )

                    if state is None:
                        if session.playback_status in (
                            ItemStatus.PLAYING,
                            ItemStatus.PAUSED,
                        ):
                            logger.info(
                                "Room %s: Spotify idle (was %s), advancing",
                                room_id,
                                session.playback_status,
                            )
                            await self._advance_queue(
                                session, room_id, host_user_id, adapter
                            )
                        backoff = settings.PLAYBACK_POLL_INTERVAL_SECONDS
                        continue

                    if state.track_id != session.current_song_id:
                        logger.info(
                            "Room %s: track changed %s -> %s, advancing",
                            room_id,
                            session.current_song_id,
                            state.track_id,
                        )
                        await self._advance_queue(
                            session, room_id, host_user_id, adapter
                        )

                    elif (
                        not state.is_playing
                        and session.playback_status == ItemStatus.PLAYING
                    ):
                        if self._is_song_ended(state):
                            logger.info(
                                "Room %s: song ended (progress=%s/%s), "
                                "advancing",
                                room_id,
                                state.progress_ms,
                                state.duration_ms,
                            )
                            await self._advance_queue(
                                session, room_id, host_user_id, adapter
                            )
                        else:
                            logger.info(
                                "Room %s: external pause detected",
                                room_id,
                            )
                            await asyncio.to_thread(
                                self._update_session_status,
                                session.id,
                                ItemStatus.PAUSED,
                            )
                            await self._broadcast_state_changed(
                                room_id, "paused", state.track_id
                            )
                    elif (
                        state.is_playing
                        and session.playback_status == ItemStatus.PAUSED
                    ):
                        await asyncio.to_thread(
                            self._update_session_status,
                            session.id,
                            ItemStatus.PLAYING,
                        )
                        await self._broadcast_state_changed(
                            room_id, "playing", state.track_id
                        )
                    elif (
                        not state.is_playing
                        and session.playback_status == ItemStatus.PAUSED
                        and self._is_song_ended(state)
                    ):
                        logger.info(
                            "Room %s: song ended while paused "
                            "(progress=%s/%s), advancing",
                            room_id,
                            state.progress_ms,
                            state.duration_ms,
                        )
                        await self._advance_queue(
                            session, room_id, host_user_id, adapter
                        )

                    backoff = settings.PLAYBACK_POLL_INTERVAL_SECONDS

                except asyncio.CancelledError:
                    raise
                except httpx.HTTPStatusError as error:
                    if error.response.status_code == 429:
                        retry_after = int(
                            error.response.headers.get("Retry-After", "5")
                        )
                        backoff = retry_after
                        logger.warning(
                            "Rate limited polling room %s, backing off %ds",
                            room_id,
                            retry_after,
                        )
                    elif error.response.status_code == 401:
                        backoff = settings.PLAYBACK_POLL_INTERVAL_SECONDS
                        logger.info(
                            "Token expired for room %s, will refresh next cycle",
                            room_id,
                        )
                    else:
                        backoff = min(backoff * 2, max_backoff)
                        logger.warning(
                            "Spotify error polling room %s: HTTP %d",
                            room_id,
                            error.response.status_code,
                        )
                except Exception:
                    backoff = min(backoff * 2, max_backoff)
                    logger.exception("Unexpected error polling room %s", room_id)

        finally:
            self._active_tasks.pop(room_id, None)
