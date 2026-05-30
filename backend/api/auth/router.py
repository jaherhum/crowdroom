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
from backend.core.exceptions import OAuthStateException
from backend.db.models.user import User
from backend.schemas.auth import (
    LocalLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.schemas.user import UserRead
from backend.services.auth_service import AuthService
from backend.services.spotify_oauth_service import SpotifyOAuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    register_request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserRead:
    """Registers a new user (ONLINE mode only).

    Args:
        register_request (RegisterRequest): The registration details.
        auth_service (AuthService): The authentication service.

    Returns:
        UserRead: The newly created user.

    Raises:
        HTTPException: 404 if AUTH_MODE is LOCAL.
    """
    if settings.AUTH_MODE != "ONLINE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in LOCAL mode",
        )
    return auth_service.register_user(register_request)


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
    return auth_service.login_user(login_request)


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
    return auth_service.local_login(login_request)


@router.get("/spotify")
def initiate_spotify_oauth(
    current_user: User = Depends(get_current_user),
    spotify_oauth_service: SpotifyOAuthService = Depends(get_spotify_oauth_service),
) -> RedirectResponse:
    """Redirect the authenticated user to Spotify's authorization page.

    Args:
        current_user: Authenticated user from JWT.
        spotify_oauth_service: OAuth service from DI.

    Returns:
        307 redirect to Spotify's authorize URL.

    Raises:
        HTTPException: 503 if Spotify OAuth is not configured.
    """
    if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spotify OAuth is not configured",
        )
    url = spotify_oauth_service.generate_authorization_url(current_user.id)
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
