"""Tests for SpotifyOAuthService."""

# ruff: noqa: D101, D102
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest

from backend.core.encryption import decrypt_data, encrypt_data
from backend.core.exceptions import OAuthStateException
from backend.db.models.enum import StreamingPlatforms
from backend.db.models.platform_connection import PlatformConnection
from backend.services.platform_connection_service import PlatformConnectionService
from backend.services.spotify_oauth_service import (
    SPOTIFY_AUTHORIZE_URL,
    SPOTIFY_OAUTH_SCOPES,
    SpotifyOAuthService,
)


class TestGenerateAuthorizationUrl:
    @pytest.fixture
    def mock_platform_service(self):
        return MagicMock(spec=PlatformConnectionService)

    @pytest.fixture
    def service(self, mock_platform_service):
        return SpotifyOAuthService(mock_platform_service)

    def test_url_starts_with_spotify_authorize(self, service):
        user_id = uuid4()
        url = service.generate_authorization_url(user_id)
        assert url.startswith(SPOTIFY_AUTHORIZE_URL)

    def test_url_contains_required_params(self, service):
        user_id = uuid4()
        url = service.generate_authorization_url(user_id)
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

        assert "client_id" in params
        assert params["response_type"] == ["code"]
        assert params["code_challenge_method"] == ["S256"]
        assert "code_challenge" in params
        assert "state" in params
        assert "redirect_uri" in params
        assert "scope" in params

    def test_state_contains_user_id_and_verifier(self, service):
        user_id = uuid4()
        url = service.generate_authorization_url(user_id)
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        state = params["state"][0]
        payload = decrypt_data(state)

        assert payload["user_id"] == str(user_id)
        assert "code_verifier" in payload
        assert len(payload["code_verifier"]) >= 43

    def test_scopes_match_expected(self, service):
        user_id = uuid4()
        url = service.generate_authorization_url(user_id)
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        assert params["scope"] == [SPOTIFY_OAUTH_SCOPES]


class TestExchangeCodeForTokens:
    @pytest.fixture
    def mock_platform_service(self):
        return MagicMock(spec=PlatformConnectionService)

    @pytest.fixture
    def service(self, mock_platform_service):
        return SpotifyOAuthService(mock_platform_service)

    @patch("backend.services.spotify_oauth_service.httpx.AsyncClient")
    def test_exchange_success(self, mock_client_class, service, mock_platform_service):
        user_id = uuid4()
        code_verifier = "test_verifier_123"
        state = encrypt_data(
            {"user_id": str(user_id), "code_verifier": code_verifier}
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "spotify_access_token",
            "refresh_token": "spotify_refresh_token",
            "expires_in": 3600,
            "scope": SPOTIFY_OAUTH_SCOPES,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        mock_platform_service.store_oauth_tokens.return_value = MagicMock(
            spec=PlatformConnection
        )

        async def _run():
            return await service.exchange_code_for_tokens("auth_code_123", state)

        result = anyio.run(_run)

        assert result is not None
        mock_platform_service.store_oauth_tokens.assert_called_once()
        call_args = mock_platform_service.store_oauth_tokens.call_args
        assert call_args[0][0] == user_id
        assert call_args[0][1] == StreamingPlatforms.SPOTIFY

    def test_exchange_with_tampered_state_raises(self, service):
        async def _run():
            await service.exchange_code_for_tokens("code", "garbage_state")

        with pytest.raises(OAuthStateException):
            anyio.run(_run)

    @patch("backend.services.spotify_oauth_service.decrypt_data_with_ttl")
    def test_exchange_with_expired_state_raises(self, mock_decrypt, service):
        from cryptography.fernet import InvalidToken

        mock_decrypt.side_effect = InvalidToken()

        state = encrypt_data({"user_id": str(uuid4()), "code_verifier": "v"})

        async def _run():
            await service.exchange_code_for_tokens("code", state)

        with pytest.raises(OAuthStateException):
            anyio.run(_run)

    @patch("backend.services.spotify_oauth_service.httpx.AsyncClient")
    def test_exchange_spotify_error_propagates(
        self, mock_client_class, service
    ):
        import httpx

        user_id = uuid4()
        state = encrypt_data(
            {"user_id": str(user_id), "code_verifier": "verifier"}
        )

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        async def _run():
            await service.exchange_code_for_tokens("code", state)

        with pytest.raises(httpx.HTTPStatusError):
            anyio.run(_run)


class TestDeriveCodeChallenge:
    def test_challenge_is_base64url_without_padding(self):
        challenge = SpotifyOAuthService._derive_code_challenge("test_verifier")
        assert "=" not in challenge
        assert "+" not in challenge
        assert "/" not in challenge

    def test_same_verifier_produces_same_challenge(self):
        verifier = "consistent_verifier_value"
        challenge1 = SpotifyOAuthService._derive_code_challenge(verifier)
        challenge2 = SpotifyOAuthService._derive_code_challenge(verifier)
        assert challenge1 == challenge2

    def test_different_verifiers_produce_different_challenges(self):
        challenge1 = SpotifyOAuthService._derive_code_challenge("verifier_a")
        challenge2 = SpotifyOAuthService._derive_code_challenge("verifier_b")
        assert challenge1 != challenge2
