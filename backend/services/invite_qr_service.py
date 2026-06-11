"""Service for QR-based room invites and pushing them to LAN devices."""

import logging
from typing import Callable
from urllib.parse import urlunparse
from uuid import UUID

import httpx

from backend.core.config import Settings
from backend.core.exceptions import DeviceUnreachableException
from backend.core.invite_token import generate_long_invite_token
from backend.core.network import assert_lan_url
from backend.schemas.invite_qr import QRInviteResponse, SendToDeviceRequest
from backend.schemas.room_invite import CreateRoomInvite
from backend.services.room_invite_service import RoomInviteService
from backend.services.room_service import RoomService

logger = logging.getLogger(__name__)

DEVICE_QR_PATH = "/qr"
DEVICE_TIMEOUT_SECONDS = 3.0
QR_INVITE_TTL_HOURS = 24

HttpClientFactory = Callable[[], httpx.AsyncClient]


def _default_http_client_factory() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(DEVICE_TIMEOUT_SECONDS))


class InviteQRService:
    """Issue long-token QR invites and ship them to ESP-class LAN devices."""

    def __init__(
        self,
        invite_service: RoomInviteService,
        room_service: RoomService,
        settings: Settings,
        http_client_factory: HttpClientFactory = _default_http_client_factory,
    ) -> None:
        """Initialize the InviteQRService.

        Args:
            invite_service: Reused for token issuance and host verification.
            room_service: Used to look up room metadata (name) for the device payload.
            settings: Application settings, used to build the join URL and read the
                device shared-secret token.
            http_client_factory: Callable returning an httpx.AsyncClient.
                Replace in tests with a fake transport.
        """
        self._invite_service = invite_service
        self._room_service = room_service
        self._settings = settings
        self._http_client_factory = http_client_factory

    def create_qr_invite(self, room_id: UUID, user_id: UUID) -> QRInviteResponse:
        """Issue a fresh long-token invite for QR display.

        Args:
            room_id: Room whose invite is being issued.
            user_id: Requesting user (must be host).

        Returns:
            Response carrying the token, full join URL, and expiry.

        Raises:
            EntityNotFoundException: If the room does not exist.
            ForbiddenException: If user is not the room host.
        """
        invite = self._invite_service.create_invite(
            room_id,
            user_id,
            CreateRoomInvite(max_uses=None, expires_in_hours=QR_INVITE_TTL_HOURS),
            token_factory=generate_long_invite_token,
        )
        url = self._build_join_url(invite.token)
        return QRInviteResponse(
            token=invite.token, url=url, expires_at=invite.expires_at
        )

    async def send_to_device(
        self, room_id: UUID, user_id: UUID, payload: SendToDeviceRequest
    ) -> None:
        """POST a freshly-issued QR invite to a LAN device.

        Sends a one-shot payload of `{url, room}` to the device, authenticated
        with the configured shared secret in the `X-Device-Token` header. The
        device renders the QR once and stays idle until the next push.

        Args:
            room_id: Room whose invite is being shipped.
            user_id: Requesting user (must be host).
            payload: Device URL chosen by the host. The path is normalized
                to `/qr` when missing.

        Raises:
            EntityNotFoundException: If the room does not exist.
            ForbiddenException: If user is not the room host.
            InvalidDeviceURLException: If the device URL is not on the LAN.
            DeviceUnreachableException: If the device fails to respond in time.
        """
        device_target = self._normalize_device_url(payload.device_url)
        self._room_service.assert_host(room_id, user_id)
        invite = self.create_qr_invite(room_id, user_id)
        body = {"url": invite.url}
        headers = (
            {"X-Device-Token": self._settings.DEVICE_AUTH_TOKEN}
            if self._settings.DEVICE_AUTH_TOKEN
            else {}
        )

        try:
            async with self._http_client_factory() as client:
                response = await client.post(device_target, json=body, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DeviceUnreachableException(
                f"Device responded with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("Device push failed: %s", exc)
            raise DeviceUnreachableException(
                "Device did not respond within the timeout"
            ) from exc

    def _build_join_url(self, token: str) -> str:
        base = self._settings.FRONTEND_URL.rstrip("/")
        return f"{base}/invite?token={token}"

    @staticmethod
    def _normalize_device_url(url: str) -> str:
        """Validate URL is on LAN and append `/qr` if missing.

        If the host typed only the device root (`http://192.168.1.42` or
        `http://192.168.1.42/`), append the canonical path. If the host
        typed a custom path, leave it alone — they probably know better.
        """
        parsed = assert_lan_url(url)
        path = parsed.path
        if path in ("", "/"):
            path = DEVICE_QR_PATH
        return urlunparse(
            (parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, "")
        )
