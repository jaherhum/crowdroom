"""Service for Spotify OAuth Authorization Code flow with PKCE."""

import base64
import hashlib
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from cryptography.fernet import InvalidToken

from backend.core.config import settings
from backend.core.encryption import decrypt_data_with_ttl, encrypt_data
from backend.core.exceptions import OAuthStateException
from backend.db.models import PlatformConnection
from backend.db.models.enum import StreamingPlatforms
from backend.schemas.platform_connection import StoreOAuthTokens
from backend.services.platform_connection_service import PlatformConnectionService

SPOTIFY_OAUTH_SCOPES = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing"
)

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


class SpotifyOAuthService:
    """Handles Spotify OAuth Authorization Code flow with PKCE."""

    def __init__(self, platform_connection_service: PlatformConnectionService):
        """Initialize with platform connection service for token storage.

        Args:
            platform_connection_service: Service for persisting OAuth tokens.
        """
        self._platform_connection_service = platform_connection_service

    def generate_authorization_url(self, user_id: UUID) -> str:
        """Build the Spotify authorization URL with PKCE challenge and encrypted state.

        Uses per-user app credentials if available, falls back to settings.

        Args:
            user_id: The authenticated user initiating the OAuth flow.

        Returns:
            Full Spotify authorization URL to redirect the user to.
        """
        client_id = self._resolve_client_id(user_id)

        code_verifier = secrets.token_urlsafe(96)
        code_challenge = self._derive_code_challenge(code_verifier)

        state_payload = {"user_id": str(user_id), "code_verifier": code_verifier}
        state = encrypt_data(state_payload)

        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
            "scope": SPOTIFY_OAUTH_SCOPES,
            "state": state,
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
        }

        return f"{SPOTIFY_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_tokens(
        self, code: str, state: str
    ) -> PlatformConnection:
        """Exchange an authorization code for tokens and persist them.

        Uses per-user app credentials if available, falls back to settings.

        Args:
            code: Authorization code received from Spotify callback.
            state: Encrypted state containing user_id and code_verifier.

        Returns:
            The created or updated PlatformConnection.

        Raises:
            OAuthStateException: If the state is invalid or expired.
        """
        try:
            state_payload = decrypt_data_with_ttl(
                state, settings.SPOTIFY_OAUTH_STATE_TTL_SECONDS
            )
        except InvalidToken as exc:
            raise OAuthStateException("State expired or tampered") from exc

        user_id = UUID(state_payload["user_id"])
        code_verifier = state_payload["code_verifier"]

        client_id, client_secret = self._resolve_credentials(user_id)
        token_response = await self._request_tokens(
            code, code_verifier, client_id, client_secret
        )

        tokens = StoreOAuthTokens(
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(seconds=token_response["expires_in"]),
            scopes=token_response.get("scope", SPOTIFY_OAUTH_SCOPES),
        )

        return self._platform_connection_service.store_oauth_tokens(
            user_id, StreamingPlatforms.SPOTIFY, tokens
        )

    async def _request_tokens(
        self,
        code: str,
        code_verifier: str,
        client_id: str,
        client_secret: str,
    ) -> dict:
        """POST to Spotify token endpoint to exchange code for tokens.

        Args:
            code: Authorization code from Spotify.
            code_verifier: PKCE verifier to prove code ownership.
            client_id: Spotify app client ID.
            client_secret: Spotify app client secret.

        Returns:
            Token response dictionary from Spotify.

        Raises:
            httpx.HTTPStatusError: If Spotify rejects the token request.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=SPOTIFY_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            return response.json()

    def _resolve_client_id(self, user_id: UUID) -> str:
        """Get client_id for OAuth from user's stored app credentials.

        Raises:
            InvalidPlatformCredentialsException: If no credentials stored.
        """
        creds = self._platform_connection_service.get_spotify_app_credentials(
            user_id
        )
        if creds and creds.get("client_id"):
            return creds["client_id"]
        from backend.core.exceptions import InvalidPlatformCredentialsException

        raise InvalidPlatformCredentialsException(
            "No Spotify app credentials found. Set up your Spotify app first."
        )

    def _resolve_credentials(self, user_id: UUID) -> tuple[str, str]:
        """Get client_id and client_secret from user's stored app credentials.

        Raises:
            InvalidPlatformCredentialsException: If no credentials stored.
        """
        creds = self._platform_connection_service.get_spotify_app_credentials(
            user_id
        )
        if creds and creds.get("client_id") and creds.get("client_secret"):
            return creds["client_id"], creds["client_secret"]
        from backend.core.exceptions import InvalidPlatformCredentialsException

        raise InvalidPlatformCredentialsException(
            "No Spotify app credentials found. Set up your Spotify app first."
        )

    @staticmethod
    def _derive_code_challenge(code_verifier: str) -> str:
        """Derive S256 code challenge from a PKCE verifier.

        Args:
            code_verifier: The random verifier string.

        Returns:
            Base64url-encoded SHA256 hash without padding.
        """
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
