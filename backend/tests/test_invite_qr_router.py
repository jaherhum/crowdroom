"""Integration tests for invite-QR HTTP endpoints."""

# ruff: noqa: D101, D102
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api.auth.dependencies import get_current_user
from backend.api.invites.dependencies import get_invite_qr_service
from backend.core.exceptions import (
    DeviceUnreachableException,
    EntityNotFoundException,
    ForbiddenException,
    InvalidDeviceURLException,
)
from backend.db.models.user import User
from backend.main import app
from backend.schemas.invite_qr import QRInviteResponse
from backend.services.invite_qr_service import InviteQRService


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid4()
    return user


@pytest.fixture
def mock_qr_service():
    return MagicMock(spec=InviteQRService)


@pytest.fixture
def client(mock_user, mock_qr_service):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_invite_qr_service] = lambda: mock_qr_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestCreateQRInvite:
    def test_201_returns_payload(self, client, mock_qr_service):
        room_id = uuid4()
        mock_qr_service.create_qr_invite.return_value = QRInviteResponse(
            token="t" * 32,
            url=f"http://localhost:8000/invite?token={'t' * 32}",
            expires_at=None,
        )

        response = client.post(f"/api/v1/rooms/{room_id}/invite-qr")

        assert response.status_code == 201
        body = response.json()
        assert body["token"] == "t" * 32
        assert body["url"].endswith("t" * 32)

    def test_403_when_not_host(self, client, mock_qr_service):
        mock_qr_service.create_qr_invite.side_effect = ForbiddenException("nope")
        response = client.post(f"/api/v1/rooms/{uuid4()}/invite-qr")
        assert response.status_code == 403

    def test_404_when_room_missing(self, client, mock_qr_service):
        mock_qr_service.create_qr_invite.side_effect = EntityNotFoundException(
            "Room", uuid4()
        )
        response = client.post(f"/api/v1/rooms/{uuid4()}/invite-qr")
        assert response.status_code == 404


class TestSendToDevice:
    def _send(self, client, device_url: str = "http://192.168.1.42"):
        return client.post(
            f"/api/v1/rooms/{uuid4()}/invite-qr/send-to-device",
            json={"device_url": device_url},
        )

    def test_204_on_success(self, client, mock_qr_service):
        async def noop(*args, **kwargs):
            return None

        mock_qr_service.send_to_device.side_effect = noop
        response = self._send(client)
        assert response.status_code == 204

    def test_400_on_invalid_url(self, client, mock_qr_service):
        async def boom(*args, **kwargs):
            raise InvalidDeviceURLException("public ip")

        mock_qr_service.send_to_device.side_effect = boom
        response = self._send(client, "http://8.8.8.8")
        assert response.status_code == 400

    def test_502_on_device_unreachable(self, client, mock_qr_service):
        async def boom(*args, **kwargs):
            raise DeviceUnreachableException("timeout")

        mock_qr_service.send_to_device.side_effect = boom
        response = self._send(client)
        assert response.status_code == 502

    def test_403_when_not_host(self, client, mock_qr_service):
        async def boom(*args, **kwargs):
            raise ForbiddenException("nope")

        mock_qr_service.send_to_device.side_effect = boom
        response = self._send(client)
        assert response.status_code == 403

    def test_422_when_url_malformed(self, client, mock_qr_service):
        response = self._send(client, "not-a-url")
        assert response.status_code == 422
        mock_qr_service.send_to_device.assert_not_called()
