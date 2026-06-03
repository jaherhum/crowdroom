"""Platform connections API router."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth.dependencies import get_current_user
from backend.api.platform_connections.dependencies import (
    get_platform_connection_service,
)
from backend.core.exceptions import (
    EntityExistsException,
    EntityNotFoundException,
    InvalidPlatformCredentialsException,
)
from backend.db.models.enum import StreamingPlatforms
from backend.db.models.user import User
from backend.schemas.platform_connection import (
    CreatePlatformConnection,
    ReadPlatformConnection,
)
from backend.services.platform_connection_service import PlatformConnectionService

router = APIRouter(prefix="/platform-connections", tags=["platform_connections"])


@router.post(
    "/", response_model=ReadPlatformConnection, status_code=status.HTTP_201_CREATED
)
async def connect_platform(
    data: CreatePlatformConnection,
    service: PlatformConnectionService = Depends(get_platform_connection_service),
    current_user: User = Depends(get_current_user),
) -> ReadPlatformConnection:
    """Validate and store encrypted credentials for a streaming platform.

    Args:
        data: Platform type and raw credentials.
        service: Platform connection service from DI.
        current_user: Authenticated user from JWT.

    Returns:
        The created platform connection (without secrets).

    Raises:
        HTTPException: 400 if credentials rejected, 409 if already connected.
    """
    try:
        connection = await service.connect(current_user.id, data)
    except InvalidPlatformCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except EntityExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return ReadPlatformConnection.model_validate(connection)


@router.get(
    "/",
    response_model=list[ReadPlatformConnection],
    status_code=status.HTTP_200_OK,
)
def get_connections(
    service: PlatformConnectionService = Depends(get_platform_connection_service),
    current_user: User = Depends(get_current_user),
) -> list[ReadPlatformConnection]:
    """List all platform connections for the authenticated user.

    Args:
        service: Platform connection service from DI.
        current_user: Authenticated user from JWT.

    Returns:
        List of platform connections (secrets excluded).
    """
    connections = service.get_connections(current_user.id)
    return [ReadPlatformConnection.model_validate(c) for c in connections]


@router.get("/spotify/has-app-credentials")
def has_spotify_app_credentials(
    service: PlatformConnectionService = Depends(get_platform_connection_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Check if user has stored Spotify app credentials (client_id/secret).

    Args:
        service: Platform connection service from DI.
        current_user: Authenticated user from JWT.

    Returns:
        Dict with has_credentials boolean.
    """
    creds = service.get_spotify_app_credentials(current_user.id)
    return {"has_credentials": creds is not None}


@router.delete("/{platform}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_platform(
    platform: StreamingPlatforms,
    service: PlatformConnectionService = Depends(get_platform_connection_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a user's connection to a streaming platform.

    Args:
        platform: The platform to disconnect from.
        service: Platform connection service from DI.
        current_user: Authenticated user from JWT.

    Raises:
        HTTPException: 404 if no connection exists for this platform.
    """
    try:
        service.disconnect(current_user.id, platform)
    except EntityNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
