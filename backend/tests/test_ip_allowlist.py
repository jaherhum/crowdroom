"""Tests for the docs IP allowlist helpers."""

# ruff: noqa: D101, D102, D103
import pytest

from backend.core.network import is_ip_allowed, parse_ip_networks


class TestParseIpNetworks:
    def test_parses_plain_ips_as_host_networks(self):
        nets = parse_ip_networks("127.0.0.1,::1")
        assert [str(n) for n in nets] == ["127.0.0.1/32", "::1/128"]

    def test_parses_cidr_ranges(self):
        nets = parse_ip_networks("10.0.0.0/8, 192.168.1.0/24")
        assert [str(n) for n in nets] == ["10.0.0.0/8", "192.168.1.0/24"]

    def test_skips_blank_and_invalid_entries(self):
        nets = parse_ip_networks("127.0.0.1, , not-an-ip, 999.999.0.0/8")
        assert [str(n) for n in nets] == ["127.0.0.1/32"]

    def test_empty_string_yields_empty_list(self):
        assert parse_ip_networks("") == []


class TestIsIpAllowed:
    def test_plain_ip_match(self):
        nets = parse_ip_networks("127.0.0.1,::1")
        assert is_ip_allowed("127.0.0.1", nets) is True
        assert is_ip_allowed("::1", nets) is True

    def test_ip_not_in_list_rejected(self):
        nets = parse_ip_networks("127.0.0.1")
        assert is_ip_allowed("10.0.0.5", nets) is False

    def test_ipv4_cidr_match(self):
        nets = parse_ip_networks("10.0.0.0/8")
        assert is_ip_allowed("10.1.2.3", nets) is True
        assert is_ip_allowed("11.0.0.1", nets) is False

    def test_ipv6_cidr_match(self):
        nets = parse_ip_networks("2001:db8::/32")
        assert is_ip_allowed("2001:db8::1", nets) is True
        assert is_ip_allowed("2001:dead::1", nets) is False

    def test_ipv4_mapped_ipv6_normalised(self):
        nets = parse_ip_networks("127.0.0.1")
        assert is_ip_allowed("::ffff:127.0.0.1", nets) is True

    @pytest.mark.parametrize("value", [None, "", "not-an-ip", "999.1.1.1"])
    def test_missing_or_malformed_rejected(self, value):
        # Even a catch-all 0.0.0.0/0 must not match an unparseable address.
        assert is_ip_allowed(value, parse_ip_networks("0.0.0.0/0")) is False
