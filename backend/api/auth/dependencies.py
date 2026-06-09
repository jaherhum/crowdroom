"""Authentication dependencies for the API."""

from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session as DBSession

from backend.api.users.dependencies import get_user_service
from backend.core.config import settings
from backend.core.exceptions import ProfileIncompleteException
from backend.core.security import SecurityService
from backend.db.database import get_session
from backend.db.models.enum import TokenType
from backend.db.models.user import User
from backend.repositories.platform_connection_repo import PlatformConnectionRepo
from backend.services.auth_service import AuthService
from backend.services.platform_connection_service import PlatformConnectionService
from backend.services.spotify_oauth_service import SpotifyOAuthService
from backend.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


def get_security_service() -> SecurityService:
    """Provides the SecurityService instance.

    Returns:
        SecurityService: The security service instance.
    """
    from backend.core.config import settings

    return SecurityService(settings)


def get_auth_service(
    user_service: UserService = Depends(get_user_service),
    security_service: SecurityService = Depends(get_security_service),
) -> AuthService:
    """Provides the AuthService instance.

    Args:
        user_service (UserService): The user service instance.
        security_service (SecurityService): The security service instance.

    Returns:
        AuthService: The authentication service instance.
    """
    return AuthService(user_service, security_service)


def get_current_user_unchecked(
    user_service: UserService = Depends(get_user_service),
    security_service: SecurityService = Depends(get_security_service),
    token: str | None = Depends(oauth2_scheme),
    cookie_token: str | None = Cookie(default=None, alias=settings.AUTH_COOKIE_NAME),
) -> User:
    """Retrieves the current user without profile completeness checks.

    Use this for auth-related endpoints (e.g., /me, /complete-profile)
    that must remain accessible to incomplete profiles.

    The access token is read from the httpOnly auth cookie first, falling
    back to the Authorization header (for API clients and tests).

    Args:
        user_service: The user service instance.
        security_service: The security service instance.
        token: The JWT token extracted from the Authorization header (optional).
        cookie_token: The JWT token extracted from the httpOnly cookie (optional).

    Returns:
        The authenticated user model.

    Raises:
        HTTPException: If the token is invalid, expired, or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    access_token = cookie_token or token
    if not access_token:
        raise credentials_exception
    try:
        payload = security_service.decode_token(
            access_token, expected_type=TokenType.ACCESS
        )
        user_id = payload.get("sub")
        user = user_service.get_by_id(UUID(user_id))

        if not user:
            raise credentials_exception
        return user
    except HTTPException:
        raise
    except Exception as exc:
        raise credentials_exception from exc


def get_current_user(
    current_user: User = Depends(get_current_user_unchecked),
) -> User:
    """Retrieves the current authenticated user, enforcing profile completeness.

    In ONLINE mode, raises ProfileIncompleteException if the user is missing
    email or password. This forces LOCAL-mode users to complete their profile
    after a mode switch.

    Args:
        current_user: The authenticated user (unchecked).

    Returns:
        The authenticated user model.

    Raises:
        ProfileIncompleteException: If ONLINE mode and profile is incomplete.
    """
    if settings.AUTH_MODE == "ONLINE":
        missing_fields = []
        if not current_user.email:
            missing_fields.append("email")
        if not current_user.hashed_password:
            missing_fields.append("password")
        if missing_fields:
            raise ProfileIncompleteException(missing_fields)
    return current_user


def _get_platform_connection_repo(
    session: DBSession = Depends(get_session),
) -> PlatformConnectionRepo:
    """Provide a PlatformConnectionRepo (local to avoid circular import).

    Args:
        session: Database session from dependency injection.

    Returns:
        A PlatformConnectionRepo instance.
    """
    return PlatformConnectionRepo(session)


def _get_platform_connection_service(
    repo: PlatformConnectionRepo = Depends(_get_platform_connection_repo),
) -> PlatformConnectionService:
    """Provide a PlatformConnectionService (local to avoid circular import).

    Args:
        repo: PlatformConnectionRepo from dependency injection.

    Returns:
        A PlatformConnectionService instance.
    """
    return PlatformConnectionService(repo)


def get_spotify_oauth_service(
    platform_connection_service: PlatformConnectionService = Depends(
        _get_platform_connection_service,
    ),
) -> SpotifyOAuthService:
    """Provide a SpotifyOAuthService wired with its dependencies.

    Args:
        platform_connection_service: Service for persisting OAuth tokens.

    Returns:
        A SpotifyOAuthService instance.
    """
    return SpotifyOAuthService(platform_connection_service)
