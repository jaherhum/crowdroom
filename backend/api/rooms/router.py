"""Room management routes for the API."""

from uuid import UUID

from fastapi import APIRouter, Depends, status, HTTPException
from backend.api.auth.dependencies import get_current_user
from backend.api.rooms.dependencies import get_room_service
from backend.db.models.user import User
from backend.schemas.room import CreateRoom, ReadRoom, UpdateRoom
from backend.services.room_service import RoomService


router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/", response_model=list[ReadRoom], status_code=status.HTTP_200_OK)
async def get_rooms(
    room_service: RoomService = Depends(get_room_service),
) -> list[ReadRoom]:
    """Retrieves a list of all rooms.

    Args:
        room_service (RoomService): The injected room service.

    Returns:
        list[ReadRoom]: A list of room schemas.
    """
    return await room_service.get_all_rooms()


@router.get(
    "/{room_id}", response_model=ReadRoom, status_code=status.HTTP_200_OK
)
async def get_room(
    room_id: UUID, room_service: RoomService = Depends(get_room_service),
) -> ReadRoom:
    """Retrieves a specific room by its ID.

    Args:
        room_id (UUID): The unique identifier of the room.
        room_service (RoomService): The injected room service.

    Returns:
        ReadRoom: The room schema.
    """
    return await room_service.get_room(room_id)


@router.post(
    "/", response_model=ReadRoom, status_code=status.HTTP_201_CREATED
)
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
    return await room_service.create_room(room_data)


@router.patch(
    "/{room_id}", response_model=ReadRoom, status_code=status.HTTP_200_OK
)
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
    return await room_service.update_room(room_id, room_data)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: UUID, room_service: RoomService = Depends(get_room_service),
) -> None:
    """Deletes a room from the system.

    Args:
        room_id (UUID): The unique identifier of the room to delete.
        room_service (RoomService): The injected room service.
    """
    await room_service.delete_room(room_id)


@router.post("/{room_id}/join", status_code=status.HTTP_200_OK)
async def join_room(
    room_id: UUID,
    room_service: RoomService = Depends(get_room_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Joins a room.

    Args:
        room_id (UUID): The unique identifier of the room.
        room_service (RoomService): The injected room service.
        current_user (User): The currently authenticated user.

    Raises:
        HTTPException: If the room is full or user is already a member.
    """
    try:
        await room_service.join_room(current_user.id, room_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{room_id}/leave", status_code=status.HTTP_200_OK)
async def leave_room(
    room_id: UUID,
    room_service: RoomService = Depends(get_room_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Leaves a room.

    Args:
        room_id (UUID): The unique identifier of the room.
        room_service (RoomService): The injected room service.
        current_user (User): The currently authenticated user.
    """
    await room_service.leave_room(current_user.id, room_id)
