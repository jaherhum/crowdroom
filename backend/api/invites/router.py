"""API endpoints for room invite link management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth.dependencies import get_current_user
from backend.api.invites.dependencies import get_invite_service
from backend.core.exceptions import (
    EntityNotFoundException,
    ForbiddenException,
    InviteExpiredException,
)
from backend.db.models.user import User
from backend.schemas.room_invite import (
    CreateRoomInvite,
    InviteJoinResult,
    InvitePreview,
    ReadRoomInvite,
)
from backend.services.room_invite_service import RoomInviteService

router = APIRouter(prefix="/rooms", tags=["invites"])


@router.post(
    "/{room_id}/invites",
    response_model=ReadRoomInvite,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    room_id: UUID,
    data: CreateRoomInvite,
    current_user: User = Depends(get_current_user),
    invite_service: RoomInviteService = Depends(get_invite_service),
) -> ReadRoomInvite:
    """Host creates a new invite link for a room."""
    try:
        return invite_service.create_invite(room_id, current_user.id, data)
    except ForbiddenException as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{room_id}/invites",
    response_model=list[ReadRoomInvite],
    status_code=status.HTTP_200_OK,
)
async def list_invites(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    invite_service: RoomInviteService = Depends(get_invite_service),
) -> list[ReadRoomInvite]:
    """Host lists all active invites for a room."""
    try:
        return invite_service.list_invites(room_id, current_user.id)
    except ForbiddenException as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/invite/{token}",
    response_model=InvitePreview,
    status_code=status.HTTP_200_OK,
)
async def preview_invite(
    token: str,
    invite_service: RoomInviteService = Depends(get_invite_service),
) -> InvitePreview:
    """Validate invite token and return room preview info (no auth required)."""
    try:
        return invite_service.get_invite_preview(token)
    except InviteExpiredException as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/invite/{token}/join",
    response_model=InviteJoinResult,
    status_code=status.HTTP_200_OK,
)
async def join_via_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    invite_service: RoomInviteService = Depends(get_invite_service),
) -> InviteJoinResult:
    """Join a room using an invite token, bypassing PIN check."""
    try:
        return invite_service.join_via_invite(token, current_user)
    except InviteExpiredException as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete(
    "/{room_id}/invites/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_invite(
    room_id: UUID,
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    invite_service: RoomInviteService = Depends(get_invite_service),
) -> None:
    """Host revokes a specific invite."""
    try:
        invite_service.revoke_invite(room_id, invite_id, current_user.id)
    except ForbiddenException as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EntityNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
