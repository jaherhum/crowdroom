"""Tests for PlatformConnectionService."""

# ruff: noqa: D101, D102
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest

from backend.core.exceptions import EntityNotFoundException
from backend.db.models.enum import StreamingPlatforms
from backend.db.models.platform_connection import PlatformConnection
from backend.repositories.platform_connection_repo import PlatformConnectionRepo
from backend.schemas.platform_connection import CreatePlatformConnection
from backend.services.platform_connection_service import PlatformConnectionService


class TestPlatformConnectionServiceConnect:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=PlatformConnectionRepo)

    @pytest.fixture
    def service(self, mock_repo):
        return PlatformConnectionService(mock_repo)

    @patch("backend.services.platform_connection_service.SpotifyAuthAdapter")
    @patch("backend.services.platform_connection_service.encrypt_data")
    def test_connect_success(self, mock_encrypt, mock_auth, service, mock_repo):
        mock_auth.validate_credentials = AsyncMock()
        mock_encrypt.return_value = "encrypted_blob"
        mock_repo.create.return_value = MagicMock(spec=PlatformConnection)

        user_id = uuid4()
        data = CreatePlatformConnection(
            platform=StreamingPlatforms.SPOTIFY,
            credentials={"client_id": "id", "client_secret": "secret"},
        )

        async def _run():
            return await service.connect(user_id, data)

        result = anyio.run(_run)
        assert result is not None
        mock_auth.validate_credentials.assert_called_once_with(data.credentials)
        mock_encrypt.assert_called_once_with(data.credentials)
        mock_repo.create.assert_called_once()


class TestPlatformConnectionServiceGetConnections:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=PlatformConnectionRepo)

    @pytest.fixture
    def service(self, mock_repo):
        return PlatformConnectionService(mock_repo)

    def test_get_connections_returns_list(self, service, mock_repo):
        user_id = uuid4()
        expected = [MagicMock(spec=PlatformConnection)]
        mock_repo.get_all_by_user.return_value = expected

        result = service.get_connections(user_id)

        assert result == expected
        mock_repo.get_all_by_user.assert_called_once_with(user_id)


class TestPlatformConnectionServiceGetDecryptedCredentials:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=PlatformConnectionRepo)

    @pytest.fixture
    def service(self, mock_repo):
        return PlatformConnectionService(mock_repo)

    @patch("backend.services.platform_connection_service.decrypt_data")
    def test_get_decrypted_credentials_success(self, mock_decrypt, service, mock_repo):
        user_id = uuid4()
        connection = MagicMock(spec=PlatformConnection)
        connection.credentials_encrypted = "encrypted_blob"
        mock_repo.get_by_user_and_platform.return_value = connection
        mock_decrypt.return_value = {"client_id": "id", "client_secret": "secret"}

        result = service.get_decrypted_credentials(user_id, StreamingPlatforms.SPOTIFY)

        assert result == {"client_id": "id", "client_secret": "secret"}
        mock_decrypt.assert_called_once_with("encrypted_blob")

    def test_get_decrypted_credentials_not_found_raises(self, service, mock_repo):
        user_id = uuid4()
        mock_repo.get_by_user_and_platform.return_value = None

        with pytest.raises(EntityNotFoundException):
            service.get_decrypted_credentials(user_id, StreamingPlatforms.SPOTIFY)


class TestPlatformConnectionServiceDisconnect:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=PlatformConnectionRepo)

    @pytest.fixture
    def service(self, mock_repo):
        return PlatformConnectionService(mock_repo)

    def test_disconnect_success(self, service, mock_repo):
        user_id = uuid4()
        connection = MagicMock(spec=PlatformConnection)
        connection.id = uuid4()
        mock_repo.get_by_user_and_platform.return_value = connection

        service.disconnect(user_id, StreamingPlatforms.SPOTIFY)

        mock_repo.delete.assert_called_once_with(connection.id)

    def test_disconnect_not_found_raises(self, service, mock_repo):
        user_id = uuid4()
        mock_repo.get_by_user_and_platform.return_value = None

        with pytest.raises(EntityNotFoundException):
            service.disconnect(user_id, StreamingPlatforms.SPOTIFY)
