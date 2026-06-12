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
    """Provide a SessionRepository bound to the current database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        A SessionRepository instance for session data access.
    """
    return SessionRepository(session)


def get_playback_service(
    session_repo: SessionRepository = Depends(get_session_repo),
    queue_service=Depends(get_queue_service),
    queue_history_repo=Depends(get_queue_history_repo),
) -> PlaybackService:
    """Provide a PlaybackService wired with its required dependencies.

    Constructs the service with session repository, queue service for
    song management, and queue history repository for recording playback.

    Args:
        session_repo: SessionRepository from dependency injection.
        queue_service: QueueService from dependency injection.
        queue_history_repo: QueueHistoryRepository from dependency injection.

    Returns:
        A fully wired PlaybackService instance.
    """
    return PlaybackService(
        session_repo=session_repo,
        queue_service=queue_service,
        queue_history_repo=queue_history_repo,
    )


def get_queue_vote_service(
    queue_vote_repo: QueueVoteRepository = Depends(get_queue_vote_repo),
    playback_service: PlaybackService = Depends(get_playback_service),
) -> QueueVoteService:
    """Provide a QueueVoteService wired with its required dependencies.

    Args:
        queue_vote_repo: QueueVoteRepository from dependency injection.
        playback_service: PlaybackService for threshold-based skip checks.

    Returns:
        A fully wired QueueVoteService instance.
    """
    return QueueVoteService(
        queue_vote_repo=queue_vote_repo,
        playback_service=playback_service,
    )


def get_session_service(
    session_repo: SessionRepository = Depends(get_session_repo),
    queue_service: QueueService = Depends(get_queue_service),
    playback_service=None,  # type: ignore[assignment]
) -> SessionService:
    """Provide a SessionService wired with its required dependencies.

    Args:
        session_repo: SessionRepository from dependency injection.
        queue_service: QueueService from dependency injection.
        playback_service: Optional PlaybackService for playback-aware behavior.

    Returns:
        A fully wired SessionService instance.
    """
    return SessionService(
        session_repo=session_repo,
        queue_service=queue_service,
        playback_service=playback_service,
    )
