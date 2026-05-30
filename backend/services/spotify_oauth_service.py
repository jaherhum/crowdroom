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

        Args:
            user_id: The authenticated user initiating the OAuth flow.

        Returns:
            Full Spotify authorization URL to redirect the user to.
        """
        code_verifier = secrets.token_urlsafe(96)
        code_challenge = self._derive_code_challenge(code_verifier)

        state_payload = {"user_id": str(user_id), "code_verifier": code_verifier}
        state = encrypt_data(state_payload)

        params = {
            "client_id": settings.SPOTIFY_CLIENT_ID,
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

        token_response = await self._request_tokens(code, code_verifier)

        tokens = StoreOAuthTokens(
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=token_response["expires_in"]),
            scopes=token_response.get("scope", SPOTIFY_OAUTH_SCOPES),
        )

        return self._platform_connection_service.store_oauth_tokens(
            user_id, StreamingPlatforms.SPOTIFY, tokens
        )

    async def _request_tokens(self, code: str, code_verifier: str) -> dict:
        """POST to Spotify token endpoint to exchange code for tokens.

        Args:
            code: Authorization code from Spotify.
            code_verifier: PKCE verifier to prove code ownership.

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
                    "client_id": settings.SPOTIFY_CLIENT_ID,
                    "client_secret": settings.SPOTIFY_CLIENT_SECRET,
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            return response.json()

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
