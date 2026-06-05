"""Authentication routes for the API."""

import logging

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from httpx import HTTPStatusError

from backend.api.auth.dependencies import (
    get_auth_service,
    get_current_user,
    get_spotify_oauth_service,
)
from backend.core.config import settings
from backend.core.exceptions import (
    EntityExistsException,
    InvalidCredentialsException,
    OAuthStateException,
    PasswordRequiredException,
)
from backend.db.models.user import User
from backend.schemas.auth import (
    LocalLoginRequest,
    LoginRequest,
    RegisterRequest,
    SetPasswordRequest,
    TokenResponse,
)
from backend.schemas.user import UserRead
from backend.services.auth_service import AuthService
from backend.services.spotify_oauth_service import SpotifyOAuthService

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
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
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
    current_user: User = Depends(get_current_user),
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


@router.get("/spotify")
def initiate_spotify_oauth(
    token: str = Query(...),
    auth_service: AuthService = Depends(get_auth_service),
    spotify_oauth_service: SpotifyOAuthService = Depends(get_spotify_oauth_service),
) -> RedirectResponse:
    """Redirect the authenticated user to Spotify's authorization page.

    Accepts JWT via ?token= query param for browser redirects where
    Authorization headers cannot be set.

    Args:
        token: JWT access token from query string.
        auth_service: The authentication service.
        spotify_oauth_service: OAuth service from DI.

    Returns:
        307 redirect to Spotify's authorize URL.

    Raises:
        HTTPException: 401 if token invalid, 503 if Spotify not configured.
    """
    user = auth_service.resolve_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

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
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


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
