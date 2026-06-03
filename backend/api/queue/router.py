"""Queue management routes for the API."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.api.auth.dependencies import get_current_user
from backend.api.queue.dependencies import (
    get_queue_history_repo,
    get_queue_service,
)
from backend.api.session.dependencies import get_queue_vote_service
from backend.db.models.user import User
from backend.schemas.queue_history import ReadQueueHistory
from backend.schemas.queue_item import (
    CreateQueueItem,
    ReadQueueItem,
    ReadQueueItemDetail,
)
from backend.schemas.queue_vote import CreateQueueVote, ReadQueueVote
from backend.services.queue_service import QueueService
from backend.services.queue_vote_service import QueueVoteService

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get(
    "/current",
    response_model=ReadQueueItemDetail | None,
    status_code=status.HTTP_200_OK,
)
def get_current_song(
    session_id: UUID,
    queue_service: QueueService = Depends(get_queue_service),
) -> ReadQueueItemDetail | None:
    """Retrieve the currently playing song for a session.

    Returns the queue item at position 0 (the now-playing slot) with
    nested song and user data.

    Args:
        session_id: The session whose current song to retrieve.
        queue_service: Dependency-injected queue service instance.

    Returns:
        ReadQueueItemDetail with song and user info, or None if
        the session has no active playback.
    """
    item = queue_service.get_current_song(session_id)
    if item is None:
        return None
    return ReadQueueItemDetail.model_validate(item)


@router.get(
    "/", response_model=list[ReadQueueItemDetail], status_code=status.HTTP_200_OK
)
def get_queue(
    session_id: UUID,
    queue_service: QueueService = Depends(get_queue_service),
) -> list[ReadQueueItemDetail]:
    """Retrieve the full queue for a session, ordered by position.

    Returns all queued items sorted by group priority (manual first) then
    ascending position number, with nested song and user data.

    Args:
        session_id: The session whose queue to retrieve.
        queue_service: Dependency-injected queue service instance.

    Returns:
        A list of ReadQueueItemDetail schemas ordered by playback position.
    """
    items = queue_service.get_queue(session_id)
    return [ReadQueueItemDetail.model_validate(item) for item in items]


@router.post("/", response_model=ReadQueueItem, status_code=status.HTTP_201_CREATED)
async def add_to_queue(
    data: CreateQueueItem,
    queue_service: QueueService = Depends(get_queue_service),
    current_user: User = Depends(get_current_user),
) -> ReadQueueItem:
    """Add a song to the end of a specific queue group.

    Uses atomic repository logic to prevent race conditions when multiple
    users add songs simultaneously. The song is placed at position max+1
    within the specified group.

    Args:
        data: Schema containing session_id, song_id, and group name.
        queue_service: Dependency-injected queue service instance.
        current_user: Authenticated user adding the song.

    Returns:
        ReadQueueItem schema for the newly added queue item.
    """
    item = await queue_service.add_to_queue(
        session_id=data.session_id,
        song_id=data.song_id,
        added_by_user_id=current_user.id,
        group=data.group,
    )
    return ReadQueueItem.model_validate(item)


@router.delete("/{queue_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_queue(
    queue_item_id: UUID,
    queue_service: QueueService = Depends(get_queue_service),
) -> None:
    """Remove a song from the queue.

    Deletes the specified queue item and renumbers subsequent items to
    fill the gap. Requires the item to exist.

    Args:
        queue_item_id: The unique identifier of the queue item to remove.
        queue_service: Dependency-injected queue service instance.

    Raises:
        EntityNotFoundException: If no queue item exists with the given ID.
    """
    await queue_service.remove_from_queue(queue_item_id)


@router.post("/vote", response_model=ReadQueueVote, status_code=status.HTTP_201_CREATED)
async def vote_skip(
    data: CreateQueueVote,
    queue_vote_service: QueueVoteService = Depends(get_queue_vote_service),
) -> ReadQueueVote:
    """Cast a skip vote for a specific queue item.

    A user may only vote once per queue item. If the vote count reaches
    the room's skip threshold (configurable via room settings), the
    song will automatically advance to the next track.

    Args:
        data: Schema containing queue_item_id and user_id.
        queue_vote_service: Dependency-injected queue vote service instance.

    Returns:
        ReadQueueVote schema for the newly cast vote.

    Raises:
        EntityExistsException: If the user has already voted on this item.
    """
    vote = await queue_vote_service.cast_vote(
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
    queue_history_repo=Depends(get_queue_history_repo),
) -> list[ReadQueueHistory]:
    """Retrieve recent playback history for a session.

    Returns the most recently played songs, ordered by play time
    descending, up to the specified limit.

    Args:
        session_id: The session whose history to retrieve.
        limit: Maximum number of history entries to return (default 15).
        queue_history_repo: Dependency-injected queue history repository.

    Returns:
        A list of ReadQueueHistory schemas ordered by play time descending.
    """
    entries = queue_history_repo.get_by_session(session_id, limit=limit)
    return [ReadQueueHistory.model_validate(entry) for entry in entries]
