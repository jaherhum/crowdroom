"""Service for orchestrating Spotify playback control commands."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import httpx

from backend.adapters.spotify_playback_adapter import (
    SpotifyPlaybackAdapter,
    SpotifyPlaybackState,
)
from backend.api.websocket import manager
from backend.core.exceptions import EntityNotFoundException, SpotifyUpstreamException
from backend.db.models.enum import ItemStatus, StreamingPlatforms
from backend.repositories.session_repo import SessionRepository
from backend.repositories.song_repo import SongRepository
from backend.services.platform_connection_service import PlatformConnectionService
from backend.services.playback_service import PlaybackService
from backend.services.queue_service import QueueService
from backend.services.room_service import RoomService

if TYPE_CHECKING:
    from backend.services.playback_poller_service import PlaybackPollerService


def _utcnow() -> datetime:
    """Return current UTC time as naive datetime (for SQLite compat)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PlaybackControlService:
    """Orchestrates Spotify playback commands with permission and token management."""

    def __init__(
        self,
        room_service: RoomService,
        session_repo: SessionRepository,
        song_repo: SongRepository,
        platform_connection_service: PlatformConnectionService,
        playback_service: PlaybackService,
        queue_service: QueueService,
        playback_poller: "PlaybackPollerService | None" = None,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            room_service: Service for host verification.
            session_repo: Repository for session state updates.
            song_repo: Repository for song external_id resolution.
            platform_connection_service: Service for fetching user OAuth tokens.
            playback_service: Service for internal queue advancement.
            queue_service: Service for queue item retrieval.
            playback_poller: Optional poller to start on playback begin.
        """
        self._room_service = room_service
        self._session_repo = session_repo
        self._song_repo = song_repo
        self._platform_connection_service = platform_connection_service
        self._playback_service = playback_service
        self._queue_service = queue_service
        self._playback_poller = playback_poller

    async def _get_adapter(self, user_id: UUID) -> SpotifyPlaybackAdapter:
        """Obtain a playback adapter with the user's valid access token.

        Args:
            user_id: UUID of the host user whose token to use.

        Returns:
            Configured SpotifyPlaybackAdapter instance.
        """
        token = await self._platform_connection_service.get_valid_access_token(
            user_id, StreamingPlatforms.SPOTIFY
        )
        return SpotifyPlaybackAdapter(token)

    async def _get_fresh_adapter(self, user_id: UUID) -> SpotifyPlaybackAdapter:
        """Force-refresh token and return a new adapter.

        Args:
            user_id: UUID of the host user whose token to refresh.

        Returns:
            SpotifyPlaybackAdapter with a freshly refreshed token.
        """
        token = await self._platform_connection_service.force_refresh_token(
            user_id, StreamingPlatforms.SPOTIFY
        )
        return SpotifyPlaybackAdapter(token)

    async def play(
        self,
        room_id: UUID,
        user_id: UUID,
        song_id: UUID | None = None,
        device_id: str | None = None,
    ) -> None:
        """Start playback of a song on the host's Spotify.

        Args:
            room_id: The room the user is controlling.
            user_id: The authenticated user (must be host).
            song_id: Internal song UUID. Omit to resume current playback.
            device_id: Optional target device.

        Raises:
            EntityNotFoundException: If room or song not found.
            ForbiddenException: If user is not room host.
        """
        self._room_service.assert_host(room_id, user_id)

        if song_id is None:
            adapter = await self._get_adapter(user_id)
            try:
                await adapter.resume(device_id)
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 401:
                    adapter = await self._get_fresh_adapter(user_id)
                    await adapter.resume(device_id)
                else:
                    raise SpotifyUpstreamException(
                        status_code=error.response.status_code,
                        detail=self._spotify_error_detail(error),
                    ) from error
            session = self._session_repo.get_by_room(room_id)
            if session:
                self._session_repo.update(
                    session.id,
                    {
                        "playback_status": ItemStatus.PLAYING,
                        "playback_started_at": _utcnow(),
                    },
                )
            await self._broadcast_state_changed(
                room_id, "playing", session.current_song_id if session else None
            )
            if self._playback_poller and session:
                await self._playback_poller.start_polling(room_id, user_id)
            return

        song = self._song_repo.get_by_id(song_id)
        if not song:
            raise EntityNotFoundException("Song", song_id)

        adapter = await self._get_adapter(user_id)
        session = self._session_repo.get_by_room(room_id)

        already_playing = (
            session
            and session.current_song_id == song.external_id
            and session.playback_status == ItemStatus.PLAYING
        )
        if already_playing:
            if self._playback_poller and not self._playback_poller.is_polling(room_id):
                await self._playback_poller.start_polling(room_id, user_id)
            return

        is_resume = (
            session
            and session.current_song_id == song.external_id
            and session.playback_status == ItemStatus.PAUSED
        )

        try:
            if is_resume:
                await adapter.resume(device_id)
            else:
                track_uri = f"spotify:track:{song.external_id}"
                await adapter.play(track_uri, device_id)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 401:
                adapter = await self._get_fresh_adapter(user_id)
                if is_resume:
                    await adapter.resume(device_id)
                else:
                    await adapter.play(track_uri, device_id)
            else:
                raise SpotifyUpstreamException(
                    status_code=error.response.status_code,
                    detail=self._spotify_error_detail(error),
                ) from error

        now = _utcnow()
        resume_position = session.playback_position_ms or 0 if is_resume else 0

        if session:
            self._session_repo.update(
                session.id,
                {
                    "playback_status": ItemStatus.PLAYING,
                    "current_song_id": song.external_id,
                    "current_device_id": device_id or session.current_device_id,
                    "playback_started_at": now,
                    "playback_position_ms": resume_position,
                },
            )

        await self._broadcast_state_changed(room_id, "playing", song.external_id)

        if self._playback_poller:
            await self._playback_poller.start_polling(room_id, user_id)

    async def pause(self, room_id: UUID, user_id: UUID) -> None:
        """Pause playback on the host's Spotify.

        Args:
            room_id: The room the user is controlling.
            user_id: The authenticated user (must be host).

        Raises:
            EntityNotFoundException: If room not found.
            ForbiddenException: If user is not room host.
        """
        self._room_service.assert_host(room_id, user_id)
        adapter = await self._get_adapter(user_id)
        try:
            await adapter.pause()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 401:
                adapter = await self._get_fresh_adapter(user_id)
                await adapter.pause()
            else:
                raise SpotifyUpstreamException(
                    status_code=error.response.status_code,
                    detail=self._spotify_error_detail(error),
                ) from error

        session = self._session_repo.get_by_room(room_id)
        if session and session.playback_started_at:
            now = _utcnow()
            started = session.playback_started_at.replace(tzinfo=None)
            elapsed = int((now - started).total_seconds() * 1000)
            position = (session.playback_position_ms or 0) + elapsed
            self._session_repo.update(
                session.id,
                {
                    "playback_status": ItemStatus.PAUSED,
                    "playback_position_ms": position,
                },
            )
        elif session:
            self._session_repo.update(
                session.id, {"playback_status": ItemStatus.PAUSED}
            )

        await self._broadcast_state_changed(room_id, "paused")

    async def skip(self, room_id: UUID, user_id: UUID) -> None:
        """Skip the current song and play CrowdRoom's next queued track.

        Args:
            room_id: The room the user is controlling.
            user_id: The authenticated user (must be host).

        Raises:
            EntityNotFoundException: If room not found.
            ForbiddenException: If user is not room host.
        """
        self._room_service.assert_host(room_id, user_id)

        session = self._session_repo.get_by_room(room_id)
        if session:
            await self._playback_service.finish_song(session.id)

        next_item = self._queue_service.get_current_song(session.id)
        if next_item and next_item.song:
            track_uri = f"spotify:track:{next_item.song.external_id}"
            adapter = await self._get_adapter(user_id)
            try:
                await adapter.play(track_uri)
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 401:
                    adapter = await self._get_fresh_adapter(user_id)
                    await adapter.play(track_uri)
                else:
                    raise SpotifyUpstreamException(
                        status_code=error.response.status_code,
                        detail=self._spotify_error_detail(error),
                    ) from error
            self._session_repo.update(
                session.id,
                {
                    "playback_status": ItemStatus.PLAYING,
                    "current_song_id": next_item.song.external_id,
                    "playback_started_at": _utcnow(),
                    "playback_position_ms": 0,
                },
            )
            await self._broadcast_state_changed(
                room_id, "playing", next_item.song.external_id
            )
            if self._playback_poller:
                await self._playback_poller.start_polling(room_id, user_id)
        else:
            adapter = await self._get_adapter(user_id)
            try:
                await adapter.pause()
            except httpx.HTTPStatusError:
                pass
            if session:
                self._session_repo.update(
                    session.id, {"playback_status": ItemStatus.STOPPED}
                )
            await self._broadcast_state_changed(room_id, "stopped")

    async def get_current_playback(
        self, room_id: UUID, user_id: UUID
    ) -> SpotifyPlaybackState | None:
        """Get current playback state from host's Spotify.

        Args:
            room_id: The room to query.
            user_id: The authenticated user (must be host).

        Returns:
            Current playback state or None if nothing is active.

        Raises:
            EntityNotFoundException: If room not found.
            ForbiddenException: If user is not room host.
        """
        self._room_service.assert_host(room_id, user_id)
        adapter = await self._get_adapter(user_id)
        try:
            return await adapter.get_current_playback()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 401:
                adapter = await self._get_fresh_adapter(user_id)
                return await adapter.get_current_playback()
            raise SpotifyUpstreamException(
                status_code=error.response.status_code,
                detail=self._spotify_error_detail(error),
            ) from error

    async def _broadcast_state_changed(
        self, room_id: UUID, playback_status: str, track_id: str | None = None
    ) -> None:
        """Broadcast playback state change to all room members.

        Args:
            room_id: Room whose members should receive the event.
            playback_status: New status ('playing', 'paused', or 'skipped').
            track_id: Spotify track ID currently playing, if any.
        """
        await manager.broadcast(
            {
                "type": "playback_state_changed",
                "room_id": str(room_id),
                "status": playback_status,
                "track_id": track_id,
            },
            str(room_id),
        )

    @staticmethod
    def _spotify_error_detail(error: httpx.HTTPStatusError) -> str:
        """Map Spotify HTTP status codes to user-facing messages.

        Args:
            error: The HTTP error raised by the Spotify adapter.

        Returns:
            Human-readable error description.
        """
        code = error.response.status_code
        if code == 404:
            return (
                "No active Spotify device found. "
                "Open Spotify on a device and try again."
            )
        if code == 401:
            return "Spotify session expired. Please re-link your Spotify account."
        if code == 403:
            return "Spotify rejected the request. Check your account permissions."
        return f"Spotify returned an error (HTTP {code})."
