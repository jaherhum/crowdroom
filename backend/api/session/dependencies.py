"""Session API dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlmodel import Session as DBSession

from backend.api.queue.dependencies import (
    get_queue_history_repo,
    get_queue_service,
    get_queue_vote_repo,
)
from backend.db.database import get_session
from backend.repositories.queue_vote_repo import QueueVoteRepository
from backend.repositories.session_repo import SessionRepository
from backend.services.playback_service import PlaybackService
from backend.services.queue_service import QueueService
from backend.services.queue_vote_service import QueueVoteService
from backend.services.session_service import SessionService


def get_session_repo(session: DBSession = Depends(get_session)) -> SessionRepository:
    """Dependency that provides a SessionRepository instance."""
    return SessionRepository(session)


def get_session_service(
    session_repo: SessionRepository = Depends(get_session_repo),
    queue_service: QueueService = Depends(get_queue_service),
    playback_service: PlaybackService | None = None,
) -> SessionService:
    """Dependency that provides a SessionService instance."""
    return SessionService(
        session_repo=session_repo,
        queue_service=queue_service,
        playback_service=playback_service,
    )


def get_queue_vote_service(
    queue_vote_repo: QueueVoteRepository = Depends(get_queue_vote_repo),
    session_service: SessionService = Depends(get_session_service),
) -> QueueVoteService:
    """Dependency that provides a QueueVoteService instance."""
    return QueueVoteService(
        queue_vote_repo=queue_vote_repo,
        session_service=session_service,
    )


def get_playback_service(
    session_repo: SessionRepository = Depends(get_session_repo),
    queue_service=Depends(get_queue_service),
    queue_history_repo=Depends(get_queue_history_repo),
) -> PlaybackService:
    """Dependency that provides a PlaybackService instance."""
    return PlaybackService(
        session_repo=session_repo,
        queue_service=queue_service,
        queue_history_repo=queue_history_repo,
    )
