"""Network helpers — LAN-only URL validation for SSRF protection."""

import ipaddress
from urllib.parse import ParseResult, urlparse

from backend.core.exceptions import InvalidDeviceURLException

ALLOWED_SCHEMES = ("http", "https")


def assert_lan_url(url: str) -> ParseResult:
    """Validate that a URL points at a private LAN address.

    Accepts:
        - Literal IPv4/IPv6 addresses in private (RFC1918), loopback, or
          link-local ranges.
        - Hostnames ending in `.local` (mDNS / Bonjour / Avahi).

    The validator does NOT perform DNS resolution: a hostname like
    `example.com` is rejected purely on shape, and a hostname like
    `evil.local` is accepted on shape. Hostname-based acceptance is
    therefore a soft guarantee — the only hard guarantee is on literal
    IP inputs. This matches the threat model: hosts on a typical LAN
    expose ESP devices via mDNS or static IPs, and resolving DNS in the
    validator would re-introduce DNS rebinding risk.

    Args:
        url: The URL to validate.

    Returns:
        The parsed URL.

    Raises:
        InvalidDeviceURLException: If the URL does not target a LAN address.
    """
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise InvalidDeviceURLException(f"Malformed URL: {exc}") from exc

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise InvalidDeviceURLException(
            f"Scheme '{parsed.scheme}' not allowed; use http or https"
        )

    host = parsed.hostname
    if not host:
        raise InvalidDeviceURLException("URL has no host")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if host.endswith(".local"):
            return parsed
        raise InvalidDeviceURLException(
            "Hostname must be a private IP literal or a .local mDNS name"
        ) from None

    if ip.is_private or ip.is_loopback or ip.is_link_local:
        return parsed

    raise InvalidDeviceURLException(
        f"Address {host} is not in a private/loopback/link-local range"
    )
