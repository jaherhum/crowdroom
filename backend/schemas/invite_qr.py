"""Schemas for QR-based room invite flow."""

from datetime import datetime

from pydantic import BaseModel, Field


class QRInviteResponse(BaseModel):
    """Response for a freshly-issued QR invite."""

    token: str = Field(description="Long-form invite token (32-char base62).")
    url: str = Field(description="Full join URL to encode in the QR.")
    expires_at: datetime | None = Field(
        default=None, description="When the invite stops being valid."
    )


class SendToDeviceRequest(BaseModel):
    """Body of POST /rooms/{id}/invite-qr/send-to-device.

    `device_url` may be the device root (`http://192.168.1.42`) — the path
    `/qr` is appended server-side when missing. The URL is validated in
    the service layer so malformed input surfaces as a 400 with a
    human-readable detail rather than a 422 pydantic schema error.
    """

    device_url: str = Field(
        min_length=1,
        description="LAN device URL (http/https, RFC1918/loopback IP or .local host).",
    )
