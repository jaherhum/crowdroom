"""Tests for the Spotify OAuth initiation route (/auth/spotify/start)."""

from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.auth.dependencies import (
    get_current_user_unchecked,
    get_spotify_oauth_service,
)
from backend.api.auth.router import router
from backend.db.models.user import User


def _build_client(mock_user, mock_oauth_service):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user_unchecked] = lambda: mock_user
    app.dependency_overrides[get_spotify_oauth_service] = lambda: mock_oauth_service
    return TestClient(app)


def test_start_spotify_oauth_returns_authorize_url():
    """Returns the Spotify authorize URL without a JWT in the query string."""
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid4()

    mock_oauth_service = MagicMock()
    creds_mock = mock_oauth_service._platform_connection_service
    creds_mock.get_spotify_app_credentials.return_value = {
        "client_id": "id",
        "client_secret": "secret",
    }
    authorize_url = "https://accounts.spotify.com/authorize?client_id=id&state=enc"
    mock_oauth_service.generate_authorization_url.return_value = authorize_url

    client = _build_client(mock_user, mock_oauth_service)

    response = client.post("/api/v1/auth/spotify/start")

    assert response.status_code == 200
    assert response.json() == {"authorize_url": authorize_url}
    mock_oauth_service.generate_authorization_url.assert_called_once_with(mock_user.id)


def test_start_spotify_oauth_without_credentials_returns_503():
    """Returns 503 when the user has no Spotify app credentials configured."""
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid4()

    mock_oauth_service = MagicMock()
    creds_mock = mock_oauth_service._platform_connection_service
    creds_mock.get_spotify_app_credentials.return_value = None

    client = _build_client(mock_user, mock_oauth_service)

    response = client.post("/api/v1/auth/spotify/start")

    assert response.status_code == 503
    mock_oauth_service.generate_authorization_url.assert_not_called()
