"""Room management routes for the API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth.dependencies import get_current_user
from backend.api.queue.dependencies import get_queue_history_repo
from backend.api.rooms.dependencies import (
    get_room_membership_service,
    get_room_service,
    get_session_repo,
)
from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    UserAlreadyInRoomException,
)
from backend.db.models.user import User
from backend.repositories.queue_history_repo import QueueHistoryRepository
from backend.schemas.queue_history import ReadQueueHistory
from backend.schemas.room import CreateRoom, JoinRoom, ReadRoom, UpdateRoom
from backend.services.room_membership_service import RoomMembershipService
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


@router.post("/", response_model=ReadRoom, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: CreateRoom,
    room_service: RoomService = Depends(get_room_service),
) -> ReadRoom:
    """Creates a new room.

    Args:
        room_data (CreateRoom): The schema containing room creation details.
        room_service (RoomService): The injected room service.

    Returns:
        ReadRoom: The newly created room schema.
    """
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
    room_service: RoomService = Depends(get_room_service),
) -> None:
    """Deletes a room from the system.

    Args:
        room_id (UUID): The unique identifier of the room to delete.
        room_service (RoomService): The injected room service.
    """
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
    membership_service: RoomMembershipService = Depends(
        get_room_membership_service
    ),
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
    membership_service: RoomMembershipService = Depends(
        get_room_membership_service
    ),
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
        raise HTTPException(
            status_code=400, detail="User is not in this room"
        )
    try:
        await membership_service.leave_room(current_user)
        return {"message": "Left room successfully"}
    except EntityNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

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
