"""Tests for InviteQRService."""

# ruff: noqa: D101, D102
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import anyio
import httpx
import pytest

from backend.core.config import Settings
from backend.core.exceptions import (
    DeviceUnreachableException,
    ForbiddenException,
    InvalidDeviceURLException,
)
from backend.db.models.room_invite import RoomInvite
from backend.schemas.invite_qr import SendToDeviceRequest
from backend.schemas.room_invite import CreateRoomInvite
from backend.services.invite_qr_service import (
    DEVICE_QR_PATH,
    QR_INVITE_TTL_HOURS,
    InviteQRService,
)
from backend.services.room_invite_service import RoomInviteService
from backend.services.room_service import RoomService


def _ok_response(url: str = "http://device.local") -> httpx.Response:
    return httpx.Response(200, request=httpx.Request("POST", url))


class _FakeAsyncClient:
    def __init__(
        self,
        response: httpx.Response | None = None,
        exc: Exception | None = None,
    ):
        self.response = response
        self.exc = exc
        self.requests: list[tuple[str, dict, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(
        self, url: str, *, json: dict, headers: dict | None = None
    ) -> httpx.Response:
        self.requests.append((url, json, headers or {}))
        if self.exc is not None:
            raise self.exc
        return self.response


def _settings(
    frontend_url: str = "http://localhost:8000",
    device_auth_token: str = "",
) -> Settings:
    return Settings(
        SECRET_KEY="x",
        ENCRYPTION_KEY="x" * 32,
        FRONTEND_URL=frontend_url,
        DEVICE_AUTH_TOKEN=device_auth_token,
    )


class TestCreateQRInvite:
    @pytest.fixture
    def mock_invite_service(self):
        return MagicMock(spec=RoomInviteService)

    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def host_user_id(self):
        return uuid4()

    @pytest.fixture
    def room_id(self):
        return uuid4()

    def _stub_invite(self, token: str = "a" * 32) -> RoomInvite:
        invite = MagicMock(spec=RoomInvite)
        invite.token = token
        invite.expires_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
        return invite

    def test_create_qr_invite_uses_long_token_and_24h_ttl(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite()
        service = InviteQRService(mock_invite_service, mock_room_service, _settings())

        result = service.create_qr_invite(room_id, host_user_id)

        call = mock_invite_service.create_invite.call_args
        passed_data: CreateRoomInvite = call.args[2]
        assert passed_data.max_uses is None
        assert passed_data.expires_in_hours == QR_INVITE_TTL_HOURS
        # token_factory must be the long generator
        assert call.kwargs["token_factory"].__name__ == "generate_long_invite_token"
        assert result.token == "a" * 32
        assert result.url == f"http://localhost:8000/invite?token={'a' * 32}"

    def test_create_qr_invite_strips_trailing_slash_from_frontend_url(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite("tok")
        service = InviteQRService(
            mock_invite_service, mock_room_service, _settings("http://example.test/")
        )

        result = service.create_qr_invite(room_id, host_user_id)

        assert result.url == "http://example.test/invite?token=tok"

    def test_create_qr_invite_propagates_forbidden(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.side_effect = ForbiddenException("nope")
        service = InviteQRService(mock_invite_service, mock_room_service, _settings())

        with pytest.raises(ForbiddenException):
            service.create_qr_invite(room_id, host_user_id)


class TestSendToDevice:
    @pytest.fixture
    def mock_invite_service(self):
        return MagicMock(spec=RoomInviteService)

    @pytest.fixture
    def mock_room_service(self):
        return MagicMock(spec=RoomService)

    @pytest.fixture
    def host_user_id(self):
        return uuid4()

    @pytest.fixture
    def room_id(self):
        return uuid4()

    def _service_with_client(
        self,
        mock_invite_service,
        mock_room_service,
        fake_client,
        device_auth_token: str = "",
    ):
        return InviteQRService(
            mock_invite_service,
            mock_room_service,
            _settings(device_auth_token=device_auth_token),
            http_client_factory=lambda: fake_client,
        )

    def _stub_invite(self, token: str = "x" * 32) -> RoomInvite:
        invite = MagicMock(spec=RoomInvite)
        invite.token = token
        invite.expires_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
        return invite

    def test_appends_path_when_root(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite()
        fake = _FakeAsyncClient(response=_ok_response())
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url="http://192.168.1.42")

        anyio.run(service.send_to_device, room_id, host_user_id, payload)

        sent_url, sent_body, _ = fake.requests[0]
        assert sent_url == f"http://192.168.1.42{DEVICE_QR_PATH}"
        assert sent_body == {
            "url": f"http://localhost:8000/invite?token={'x' * 32}",
        }

    def test_appends_path_when_only_slash(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite()
        fake = _FakeAsyncClient(response=_ok_response())
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url="http://192.168.1.42/")

        anyio.run(service.send_to_device, room_id, host_user_id, payload)

        assert fake.requests[0][0] == f"http://192.168.1.42{DEVICE_QR_PATH}"

    def test_keeps_custom_path(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite()
        fake = _FakeAsyncClient(response=_ok_response())
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url="http://192.168.1.42/foo")

        anyio.run(service.send_to_device, room_id, host_user_id, payload)

        assert fake.requests[0][0] == "http://192.168.1.42/foo"

    def test_sends_device_auth_token_header_when_configured(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite()
        fake = _FakeAsyncClient(response=_ok_response())
        service = self._service_with_client(
            mock_invite_service,
            mock_room_service,
            fake,
            device_auth_token="secret-shared-token",
        )
        payload = SendToDeviceRequest(device_url="http://192.168.1.42")

        anyio.run(service.send_to_device, room_id, host_user_id, payload)

        _, _, headers = fake.requests[0]
        assert headers.get("X-Device-Token") == "secret-shared-token"

    def test_omits_device_auth_token_header_when_not_configured(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite()
        fake = _FakeAsyncClient(response=_ok_response())
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url="http://192.168.1.42")

        anyio.run(service.send_to_device, room_id, host_user_id, payload)

        _, _, headers = fake.requests[0]
        assert "X-Device-Token" not in headers

    @pytest.mark.parametrize(
        "url",
        [
            "http://192.168.1.42",
            "http://10.0.0.5",
            "http://device.local",
            "http://127.0.0.1",
        ],
    )
    def test_accepts_lan_addresses(
        self, mock_invite_service, mock_room_service, host_user_id, room_id, url
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite()
        fake = _FakeAsyncClient(response=_ok_response())
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url=url)

        anyio.run(service.send_to_device, room_id, host_user_id, payload)

        assert fake.requests, "expected one outbound request"

    def test_rejects_public_ip(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        fake = _FakeAsyncClient()
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url="http://8.8.8.8")

        with pytest.raises(InvalidDeviceURLException):
            anyio.run(service.send_to_device, room_id, host_user_id, payload)

        assert not fake.requests
        mock_invite_service.create_invite.assert_not_called()

    @pytest.mark.parametrize(
        "url",
        [
            "http:",
            "http://",
            "ftp://192.168.1.42",
            "192.168.10.24",
            "not a url",
        ],
    )
    def test_rejects_malformed_url_with_invalid_device_url(
        self, mock_invite_service, mock_room_service, host_user_id, room_id, url
    ):
        fake = _FakeAsyncClient()
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url=url)

        with pytest.raises(InvalidDeviceURLException):
            anyio.run(service.send_to_device, room_id, host_user_id, payload)

        assert not fake.requests
        mock_invite_service.create_invite.assert_not_called()

    def test_timeout_maps_to_device_unreachable(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite()
        fake = _FakeAsyncClient(exc=httpx.ConnectTimeout("slow"))
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url="http://192.168.1.42")

        with pytest.raises(DeviceUnreachableException):
            anyio.run(service.send_to_device, room_id, host_user_id, payload)

    def test_5xx_maps_to_device_unreachable(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_invite_service.create_invite.return_value = self._stub_invite()
        fake = _FakeAsyncClient(
            response=httpx.Response(500, request=httpx.Request("POST", "http://x"))
        )
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url="http://192.168.1.42")

        with pytest.raises(DeviceUnreachableException):
            anyio.run(service.send_to_device, room_id, host_user_id, payload)

    def test_forbidden_propagates_without_calling_device(
        self, mock_invite_service, mock_room_service, host_user_id, room_id
    ):
        mock_room_service.assert_host.side_effect = ForbiddenException("nope")
        fake = _FakeAsyncClient()
        service = self._service_with_client(
            mock_invite_service, mock_room_service, fake
        )
        payload = SendToDeviceRequest(device_url="http://192.168.1.42")

        with pytest.raises(ForbiddenException):
            anyio.run(service.send_to_device, room_id, host_user_id, payload)

        assert not fake.requests
        mock_invite_service.create_invite.assert_not_called()
