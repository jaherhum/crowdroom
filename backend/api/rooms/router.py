"""Room management routes for the API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.api.auth.dependencies import get_current_user
from backend.api.queue.dependencies import get_queue_history_repo
from backend.api.rooms.dependencies import (
    get_room_membership_service,
    get_room_moderation_service,
    get_room_service,
    get_session_repo,
)
from backend.api.users.dependencies import get_user_repo
from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    UserAlreadyInRoomException,
)
from backend.db.models.user import User
from backend.repositories.queue_history_repo import QueueHistoryRepository
from backend.repositories.session_repo import SessionRepository
from backend.repositories.user_repo import UserRepository
from backend.schemas.queue_history import ReadQueueHistory
from backend.schemas.room import (
    BannedUserRead,
    CreateRoom,
    JoinRoom,
    ReadRoom,
    UpdateRoom,
)
from backend.schemas.user import UserRead
from backend.services.room_membership_service import RoomMembershipService
from backend.services.room_moderation_service import RoomModerationService
from backend.services.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/", response_model=list[ReadRoom], status_code=status.HTTP_200_OK)
async def get_rooms(
    room_service: RoomService = Depends(get_room_service),
) -> list[ReadRoom]:
    """Retrieve all publicly listable rooms.

    Returns rooms that are public or private-but-visible.
    Private+invisible rooms are excluded.

    Args:
        room_service: The injected room service.

    Returns:
        Publicly listable rooms.
    """
    return room_service.get_all_rooms()


@router.get(
    "/code/{room_code}", response_model=ReadRoom, status_code=status.HTTP_200_OK
)
async def get_room_by_code(
    room_code: str,
    room_service: RoomService = Depends(get_room_service),
) -> ReadRoom:
    """Retrieve a room by its unique sharing code.

    Args:
        room_code: The 6-character room code.
        room_service: The injected room service.

    Returns:
        ReadRoom: The room schema.
    """
    return room_service.get_room_by_code(room_code)


@router.get("/{room_id}", response_model=ReadRoom, status_code=status.HTTP_200_OK)
async def get_room(
    room_id: UUID,
    room_service: RoomService = Depends(get_room_service),
) -> ReadRoom:
    """Retrieves a specific room by its ID.

    Args:
        room_id (UUID): The unique identifier of the room.
        room_service (RoomService): The injected room service.

    Returns:
        ReadRoom: The room schema.
    """
    return room_service.get_room(room_id)


@router.get(
    "/{room_id}/members",
    response_model=list[UserRead],
    status_code=status.HTTP_200_OK,
)
async def get_room_members(
    room_id: UUID,
    room_service: RoomService = Depends(get_room_service),
    user_repo: UserRepository = Depends(get_user_repo),
) -> list[UserRead]:
    """Retrieve all users currently in a room.

    Args:
        room_id: The room whose members to list.
        room_service: The injected room service (validates room exists).
        user_repo: The injected user repository.

    Returns:
        List of users currently in the room.
    """
    room_service.get_room(room_id)
    users = user_repo.get_by_room(room_id)
    return [UserRead.model_validate(user) for user in users]


@router.post("/", response_model=ReadRoom, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: CreateRoom,
    current_user: User = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
) -> ReadRoom:
    """Creates a new room. Requires an authenticated user with a password.

    Args:
        room_data (CreateRoom): The schema containing room creation details.
        current_user (User): The authenticated user (must have a password set).
        room_service (RoomService): The injected room service.

    Returns:
        ReadRoom: The newly created room schema.
    """
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password required to create a room. Set a password first.",
        )
    room_data.host_user_id = current_user.id
    return room_service.create_room(room_data)


@router.patch("/{room_id}", response_model=ReadRoom, status_code=status.HTTP_200_OK)
async def update_room(
    room_id: UUID,
    room_data: UpdateRoom,
    room_service: RoomService = Depends(get_room_service),
) -> ReadRoom:
    """Updates an existing room.

    Args:
        room_id (UUID): The unique identifier of the room to update.
        room_data (UpdateRoom): The schema containing the fields to update.
        room_service (RoomService): The injected room service.

    Returns:
        ReadRoom: The updated room schema.
    """
    return room_service.update_room(room_id, room_data)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: UUID,
    request: Request,
    room_service: RoomService = Depends(get_room_service),
) -> None:
    """Deletes a room from the system.

    Args:
        room_id (UUID): The unique identifier of the room to delete.
        request (Request): The incoming request (used to access app state).
        room_service (RoomService): The injected room service.
    """
    await request.app.state.playback_poller.stop_polling(room_id)
    room_service.delete_room(room_id)


@router.get(
    "/{room_id}/history/",
    response_model=list[ReadQueueHistory],
    status_code=status.HTTP_200_OK,
)
async def get_room_history(
    room_id: UUID,
    limit: int = 15,
    session_repo=Depends(get_session_repo),
    queue_history_repo: QueueHistoryRepository = Depends(get_queue_history_repo),
) -> list[ReadQueueHistory]:
    """Get playback history for a room, ordered newest first.

    Resolves the unique session associated with the room and returns up to
    ``limit`` recent history entries. Returns 404 if the room has no session.

    Args:
        room_id (UUID): The unique identifier of the room.
        limit (int): Maximum number of history entries to return. Defaults to 15.
        session_repo: Session repository from DI.
        queue_history_repo: Queue history repository from DI.

    Returns:
        list[ReadQueueHistory]: The room's playback history entries.
    """
    session = session_repo.get_by_room(room_id)
    if session is None:
        raise EntityNotFoundException(entity_name="Session")

    history_entries = queue_history_repo.get_by_session(session.id, limit=limit)
    return [ReadQueueHistory.model_validate(entry) for entry in history_entries]


@router.post("/{room_id}/join", status_code=status.HTTP_200_OK)
async def join_room(
    room_id: UUID,
    body: JoinRoom,
    current_user: User = Depends(get_current_user),
    membership_service: RoomMembershipService = Depends(get_room_membership_service),
) -> dict:
    """Join a room. Public rooms join directly; private rooms need PIN or invite.

    Args:
        room_id: The room to join.
        body: Optional PIN or invite_token.
        current_user: The authenticated user.
        membership_service: The injected membership service.

    Returns:
        Confirmation with room details.
    """
    try:
        await membership_service.join_room(
            room_id,
            current_user,
            pin=body.pin,
            invite_token=body.invite_token,
        )
        return {"room_id": str(room_id), "message": "Joined room successfully"}
    except UserAlreadyInRoomException as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ForbiddenException as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{room_id}/leave", status_code=status.HTTP_200_OK)
async def leave_room(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    membership_service: RoomMembershipService = Depends(get_room_membership_service),
) -> dict:
    """Leave the current room.

    Args:
        room_id: The room to leave (validated against user state).
        current_user: The authenticated user.
        membership_service: The injected membership service.

    Returns:
        Confirmation message.
    """
    if current_user.room_id != room_id:
        raise HTTPException(status_code=400, detail="User is not in this room")
    try:
        await membership_service.leave_room(current_user)
        return {"message": "Left room successfully"}
    except EntityNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{room_id}/kick/{user_id}", status_code=status.HTTP_200_OK)
async def kick_user(
    room_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    moderation_service: RoomModerationService = Depends(get_room_moderation_service),
) -> dict:
    """Kick a member from a room. The host only; kicked users may rejoin.

    Args:
        room_id: The room to kick from.
        user_id: The member being kicked.
        current_user: The authenticated host.
        moderation_service: The injected moderation service.

    Returns:
        Confirmation message.
    """
    await moderation_service.kick_user(room_id, current_user.id, user_id)
    return {"message": "User kicked"}


@router.post("/{room_id}/ban/{user_id}", status_code=status.HTTP_200_OK)
async def ban_user(
    room_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    moderation_service: RoomModerationService = Depends(get_room_moderation_service),
) -> dict:
    """Ban a user from a room. The host only; banned users cannot rejoin.

    Args:
        room_id: The room to ban from.
        user_id: The user being banned.
        current_user: The authenticated host.
        moderation_service: The injected moderation service.

    Returns:
        Confirmation message.
    """
    await moderation_service.ban_user(room_id, current_user.id, user_id)
    return {"message": "User banned"}


@router.delete("/{room_id}/ban/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unban_user(
    room_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    moderation_service: RoomModerationService = Depends(get_room_moderation_service),
) -> None:
    """Unban a user from a room. The host only.

    Args:
        room_id: The room to unban in.
        user_id: The user being unbanned.
        current_user: The authenticated host.
        moderation_service: The injected moderation service.
    """
    moderation_service.unban_user(room_id, current_user.id, user_id)


@router.get(
    "/{room_id}/bans",
    response_model=list[BannedUserRead],
    status_code=status.HTTP_200_OK,
)
async def list_bans(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    moderation_service: RoomModerationService = Depends(get_room_moderation_service),
) -> list[BannedUserRead]:
    """List users banned from a room. The host only.

    Args:
        room_id: The room whose bans to list.
        current_user: The authenticated host.
        moderation_service: The injected moderation service.

    Returns:
        The banned users with usernames and ban timestamps.
    """
    return moderation_service.list_bans(room_id, current_user.id)


@router.get("/mine", response_model=list[ReadRoom], status_code=status.HTTP_200_OK)
async def get_my_rooms(
    current_user: User = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
) -> list[ReadRoom]:
    """Retrieve rooms owned by the authenticated user.

    Args:
        current_user: The authenticated user from JWT.
        room_service: The injected room service.

    Returns:
        The user's hosted rooms, regardless of visibility settings.
    """
    return room_service.get_host_rooms(current_user.id)


@router.get("/{room_id}/playback")
async def get_room_playback(
    request: Request,
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(get_session_repo),
) -> dict:
    """Get playback timing info for syncing progress bars.

    Also ensures the playback poller is running if session is active.

    Args:
        request: FastAPI request (for app state access).
        room_id: The room whose playback state to retrieve.
        current_user: Authenticated user.
        session_repo: The injected session repository.

    Returns:
        Dictionary with playback timing fields.
    """
    session = session_repo.get_by_room(room_id)
    if not session:
        return {"status": "stopped"}

    from datetime import datetime, timezone

    poller = request.app.state.playback_poller
    if poller and not poller.is_polling(room_id) and session.room:
        await poller.start_polling(room_id, session.room.host_user_id)

    playback_status = (
        session.playback_status.value if session.playback_status else "stopped"
    )
    base_position = session.playback_position_ms or 0
    elapsed_ms = base_position

    if playback_status == "playing" and session.playback_started_at:
        started = session.playback_started_at.replace(tzinfo=None)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed_ms = base_position + int((now - started).total_seconds() * 1000)

    return {
        "status": playback_status,
        "elapsed_ms": elapsed_ms,
        "current_song_id": session.current_song_id,
    }
