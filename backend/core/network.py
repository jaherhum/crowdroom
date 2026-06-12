"""Network helpers — LAN-only URL validation for SSRF protection."""

import ipaddress
import logging
from urllib.parse import ParseResult, urlparse

from backend.core.exceptions import InvalidDeviceURLException

ALLOWED_SCHEMES = ("http", "https")

logger = logging.getLogger(__name__)

# A parsed allowlist entry: any IPv4/IPv6 network (a plain IP is a /32 or /128).
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def parse_ip_networks(raw: str) -> list[IPNetwork]:
    """Parse a comma-separated list of IPs/CIDRs into network objects.

    Plain IPs are treated as single-host networks (/32 or /128). Invalid
    entries are skipped with a warning rather than raising, so a single
    typo in the allowlist cannot take the whole app down.

    Args:
        raw: Comma-separated IPs and/or CIDR ranges (IPv4 and IPv6).

    Returns:
        The successfully parsed networks, in input order.
    """
    networks: list[IPNetwork] = []
    for token in raw.split(","):
        entry = token.strip()
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning("Ignoring invalid IP/CIDR in allowlist: %r", entry)
    return networks


def is_ip_allowed(client_ip: str | None, allowed_networks: list[IPNetwork]) -> bool:
    """Return True if ``client_ip`` falls within any allowed network.

    IPv4-mapped IPv6 addresses (e.g. ``::ffff:127.0.0.1``) are normalised to
    their IPv4 form before matching, so an IPv4 allowlist entry still matches a
    client reported in IPv4-mapped form. A missing or malformed address is
    never allowed.

    Args:
        client_ip: The client address as a string, or None.
        allowed_networks: Networks parsed by :func:`parse_ip_networks`.

    Returns:
        True if the address is in the allowlist, False otherwise.
    """
    if not client_ip:
        return False
    try:
        ip = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    return any(ip in network for network in allowed_networks)


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
