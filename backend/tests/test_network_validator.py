"""Tests for the LAN-only URL validator."""

# ruff: noqa: D101, D102
import pytest

from backend.core.exceptions import InvalidDeviceURLException
from backend.core.network import assert_lan_url


class TestAssertLanUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "http://192.168.1.42",
            "http://192.168.1.42/",
            "http://192.168.1.42/send-crowdroom-qr",
            "http://10.0.0.5",
            "http://172.16.0.1",
            "http://127.0.0.1:8080",
            "http://[::1]",
            "http://169.254.10.1",
            "http://device.local",
            "http://printer.local/path",
            "https://192.168.1.42",
        ],
    )
    def test_accepts_lan_targets(self, url):
        parsed = assert_lan_url(url)
        assert parsed.scheme in ("http", "https")

    @pytest.mark.parametrize(
        "url",
        [
            "http://8.8.8.8",
            "http://1.1.1.1/path",
            "https://example.com",
            "http://example.com",
            "http://93.184.216.34",
            "http://[2606:4700:4700::1111]",
        ],
    )
    def test_rejects_public_targets(self, url):
        with pytest.raises(InvalidDeviceURLException):
            assert_lan_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://192.168.1.42",
            "file:///etc/passwd",
            "gopher://192.168.1.42",
        ],
    )
    def test_rejects_non_http_schemes(self, url):
        with pytest.raises(InvalidDeviceURLException):
            assert_lan_url(url)

    def test_rejects_missing_host(self):
        with pytest.raises(InvalidDeviceURLException):
            assert_lan_url("http:///path")
