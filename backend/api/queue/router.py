"""Queue management routes for the API."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.api.auth.dependencies import get_current_user
from backend.api.queue.dependencies import (
    get_queue_history_service,
    get_queue_service,
)
from backend.api.session.dependencies import get_queue_vote_service
from backend.db.models.user import User
from backend.schemas.queue_history import ReadQueueHistory
from backend.schemas.queue_item import CreateQueueItem, ReadQueueItem
from backend.schemas.queue_vote import CreateQueueVote, ReadQueueVote
from backend.services.queue_history_service import QueueHistoryService
from backend.services.queue_service import QueueService
from backend.services.queue_vote_service import QueueVoteService

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get(
    "/current",
    response_model=ReadQueueItem | None,
    status_code=status.HTTP_200_OK,
)
def get_current_song(
    session_id: UUID,
    queue_service: QueueService = Depends(get_queue_service),
) -> ReadQueueItem | None:
    """Get the currently playing song in a session queue."""
    item = queue_service.get_current_song(session_id)
    if item is None:
        return None
    return ReadQueueItem.model_validate(item)


@router.get("/", response_model=list[ReadQueueItem], status_code=status.HTTP_200_OK)
def get_queue(
    session_id: UUID,
    queue_service: QueueService = Depends(get_queue_service),
) -> list[ReadQueueItem]:
    """Get the full queue for a session, ordered by position."""
    items = queue_service.get_queue(session_id)
    return [ReadQueueItem.model_validate(item) for item in items]


@router.post("/", response_model=ReadQueueItem, status_code=status.HTTP_201_CREATED)
def add_to_queue(
    data: CreateQueueItem,
    queue_service: QueueService = Depends(get_queue_service),
    current_user: User = Depends(get_current_user),
) -> ReadQueueItem:
    """Add a song to the end of a queue group."""
    item = queue_service.add_to_queue(
        session_id=data.session_id,
        song_id=data.song_id,
        added_by_user_id=current_user.id,
        group=data.group,
    )
    return ReadQueueItem.model_validate(item)


@router.delete("/{queue_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_queue(
    queue_item_id: UUID,
    queue_service: QueueService = Depends(get_queue_service),
) -> None:
    """Remove a song from the queue."""
    queue_service.remove_from_queue(queue_item_id)


@router.post("/vote", response_model=ReadQueueVote, status_code=status.HTTP_201_CREATED)
def vote_skip(
    data: CreateQueueVote,
    queue_vote_service: QueueVoteService = Depends(get_queue_vote_service),
) -> ReadQueueVote:
    """Cast a skip vote on a queue item."""
    vote = queue_vote_service.cast_vote(
        queue_item_id=data.queue_item_id,
        user_id=data.user_id,
    )
    return ReadQueueVote.model_validate(vote)


@router.get(
    "/history/",
    response_model=list[ReadQueueHistory],
    status_code=status.HTTP_200_OK,
)
def get_history(
    session_id: UUID,
    limit: int = 15,
    queue_history_service: QueueHistoryService = Depends(get_queue_history_service),
) -> list[ReadQueueHistory]:
    """Get playback history for a session."""
    entries = queue_history_service.get_history(session_id, limit=limit)
    return [ReadQueueHistory.model_validate(entry) for entry in entries]
