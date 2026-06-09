"""Authentication routes for the API."""

import logging
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from httpx import HTTPStatusError
from PIL import Image

from backend.api.auth.dependencies import (
    get_auth_service,
    get_current_user_unchecked,
    get_spotify_oauth_service,
)
from backend.api.users.dependencies import get_user_service
from backend.core.config import settings
from backend.core.exceptions import (
    EntityExistsException,
    InvalidCredentialsException,
    OAuthStateException,
    PasswordRequiredException,
)
from backend.db.models.user import User
from backend.schemas.auth import (
    ChangePasswordRequest,
    CompleteProfileRequest,
    LocalLoginRequest,
    LoginRequest,
    RegisterRequest,
    SetPasswordRequest,
    SpotifyAuthorizeResponse,
    TokenResponse,
)
from backend.schemas.user import UserRead
from backend.services.auth_service import AuthService
from backend.services.spotify_oauth_service import SpotifyOAuthService
from backend.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/mode")
def get_auth_mode() -> dict:
    """Return the current authentication mode.

    Returns:
        Dict with the active auth mode (LOCAL or ONLINE).
    """
    return {"mode": settings.AUTH_MODE}


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user_unchecked)) -> UserRead:
    """Return the authenticated user's profile.

    Args:
        current_user: The authenticated user from JWT.

    Returns:
        The user's data including current room_id.
    """
    return UserRead.model_validate(current_user)


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register(
    register_request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Registers a new user and returns a token (ONLINE mode only).

    Args:
        register_request (RegisterRequest): The registration details.
        auth_service (AuthService): The authentication service.

    Returns:
        TokenResponse: Access token for immediate login.

    Raises:
        HTTPException: 404 if AUTH_MODE is LOCAL, 409 if user exists.
    """
    if settings.AUTH_MODE != "ONLINE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in LOCAL mode",
        )
    try:
        return auth_service.register_user(register_request)
    except EntityExistsException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(
    login_request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticates a user and returns a JWT token (ONLINE mode only).

    Args:
        login_request (LoginRequest): The login credentials.
        auth_service (AuthService): The authentication service.

    Returns:
        TokenResponse: The authentication token.

    Raises:
        HTTPException: 404 if AUTH_MODE is LOCAL.
    """
    if settings.AUTH_MODE != "ONLINE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in LOCAL mode",
        )
    try:
        return auth_service.login_user(login_request)
    except InvalidCredentialsException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post("/local-login", response_model=TokenResponse)
def local_login(
    login_request: LocalLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate with username only (LOCAL mode).

    Finds existing user or auto-creates one. No password required.
    Disabled when AUTH_MODE=ONLINE.

    Args:
        login_request: The username to login with.
        auth_service: The authentication service.

    Returns:
        TokenResponse: The authentication token.

    Raises:
        HTTPException: 404 if AUTH_MODE is not LOCAL.
    """
    if settings.AUTH_MODE != "LOCAL":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in ONLINE mode",
        )
    try:
        return auth_service.local_login(login_request)
    except PasswordRequiredException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except InvalidCredentialsException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post("/set-password", status_code=status.HTTP_204_NO_CONTENT)
def set_password(
    body: SetPasswordRequest,
    current_user: User = Depends(get_current_user_unchecked),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Set a password on a passwordless account.

    Allows guest users to upgrade their account so they can create rooms.
    Fails if the user already has a password set.

    Args:
        body: The new password.
        current_user: The authenticated user from JWT.
        auth_service: The authentication service.

    Raises:
        HTTPException: 409 if user already has a password.
    """
    if current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Password already set. Use change-password instead.",
        )
    auth_service.set_password(current_user.id, body.password.get_secret_value())


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_unchecked),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Change the user's password.

    Args:
        body: The current and new password.
        current_user: The authenticated user from JWT.
        auth_service: The authentication service.

    Raises:
        HTTPException: 401 if current password is incorrect.
    """
    try:
        auth_service.change_password(
            user=current_user,
            current_password=body.current_password.get_secret_value(),
            new_password=body.new_password.get_secret_value(),
        )
    except InvalidCredentialsException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        ) from exc


@router.post("/complete-profile", status_code=status.HTTP_204_NO_CONTENT)
def complete_profile(
    body: CompleteProfileRequest,
    current_user: User = Depends(get_current_user_unchecked),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Complete a user's profile by setting email and password.

    Required when switching from LOCAL to ONLINE mode and the user is
    missing email or password. Skips fields that are already set.

    Args:
        body: The email and password to set.
        current_user: The authenticated user from JWT.
        auth_service: The authentication service.

    Raises:
        HTTPException: 409 if email is already taken by another user.
    """
    try:
        auth_service.complete_profile(
            user=current_user,
            email=str(body.email),
            plain_password=body.password.get_secret_value(),
        )
    except EntityExistsException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


AVATARS_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "avatars"
MAX_AVATAR_SIZE = 5 * 1024 * 1024
AVATAR_MAX_PX = 256


@router.post("/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile,
    current_user: User = Depends(get_current_user_unchecked),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Upload and compress a user avatar image.

    Accepts JPEG/PNG/WebP up to 5MB. Compresses to 256x256 WebP.

    Args:
        file: The uploaded image file.
        current_user: The authenticated user.
        user_service: The user service for persisting avatar path.

    Returns:
        The updated user with avatar_url.

    Raises:
        HTTPException: 400 if file is too large or not a valid image.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WebP images are accepted.",
        )

    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be under 5MB.",
        )

    try:
        import io

        image = Image.open(io.BytesIO(contents))
        image = image.convert("RGB")
        image.thumbnail((AVATAR_MAX_PX, AVATAR_MAX_PX), Image.LANCZOS)

        filename = f"{uuid4().hex}.webp"
        output_path = AVATARS_DIR / filename
        image.save(output_path, format="WEBP", quality=80)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process image.",
        ) from exc

    if current_user.avatar_path:
        old_path = AVATARS_DIR / current_user.avatar_path
        if old_path.exists():
            old_path.unlink()

    from backend.schemas.user import UserUpdate

    return user_service.update_user(
        current_user.id, UserUpdate(avatar_path=filename)
    )


@router.post("/spotify/start", response_model=SpotifyAuthorizeResponse)
def start_spotify_oauth(
    user: User = Depends(get_current_user_unchecked),
    spotify_oauth_service: SpotifyOAuthService = Depends(get_spotify_oauth_service),
) -> SpotifyAuthorizeResponse:
    """Build the Spotify authorization URL for the authenticated user.

    Authenticates via the standard ``Authorization: Bearer`` header (so the
    JWT never travels in a URL). The frontend redirects the browser to the
    returned ``authorize_url``.

    Args:
        user: Authenticated user initiating the OAuth flow.
        spotify_oauth_service: OAuth service from DI.

    Returns:
        SpotifyAuthorizeResponse with the Spotify authorize URL.

    Raises:
        HTTPException: 503 if no Spotify app credentials are configured.
    """
    has_user_creds = bool(
        spotify_oauth_service._platform_connection_service
        .get_spotify_app_credentials(user.id)
    )
    if not has_user_creds:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No Spotify credentials configured. "
            "Please set up your Spotify app credentials first.",
        )

    url = spotify_oauth_service.generate_authorization_url(user.id)
    return SpotifyAuthorizeResponse(authorize_url=url)


@router.get("/spotify/callback")
async def spotify_oauth_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    spotify_oauth_service: SpotifyOAuthService = Depends(get_spotify_oauth_service),
) -> RedirectResponse:
    """Handle Spotify's OAuth redirect and exchange code for tokens.

    Args:
        code: Authorization code from Spotify.
        state: Encrypted state with user_id and code_verifier.
        error: Error string if user denied consent.
        spotify_oauth_service: OAuth service from DI.

    Returns:
        Redirect to frontend with success or error query params.
    """
    frontend_url = settings.FRONTEND_URL

    if error:
        return RedirectResponse(url=f"{frontend_url}?error={error}")

    if not code or not state:
        return RedirectResponse(url=f"{frontend_url}?error=missing_params")

    try:
        await spotify_oauth_service.exchange_code_for_tokens(code, state)
    except (OAuthStateException, InvalidToken):
        logger.warning("Spotify OAuth callback failed: invalid or expired state")
        return RedirectResponse(url=f"{frontend_url}?error=oauth_state_invalid")
    except HTTPStatusError as exc:
        logger.error("Spotify token exchange failed: %s", exc.response.text)
        return RedirectResponse(url=f"{frontend_url}?error=oauth_exchange_failed")

    return RedirectResponse(url=f"{frontend_url}?spotify=connected")
