"""Integration tests for gated API docs endpoints."""

# ruff: noqa: D101, D102, D103
import pytest
from fastapi.testclient import TestClient

from backend.core import config
from backend.core.network import parse_ip_networks
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def set_allowlist(monkeypatch):
    """Override the parsed docs allowlist for the duration of a test."""

    def _set(raw: str):
        monkeypatch.setattr(
            config.settings, "_docs_allowed_networks", parse_ip_networks(raw)
        )

    return _set


DOC_PATHS = ["/docs", "/redoc", "/openapi.json"]


class TestDocsAccessViaProxy:
    """Use DOCS_TRUST_PROXY so the client IP comes from X-Forwarded-For."""

    @pytest.fixture(autouse=True)
    def trust_proxy(self, monkeypatch):
        monkeypatch.setattr(config.settings, "DOCS_TRUST_PROXY", True)

    @pytest.mark.parametrize("path", DOC_PATHS)
    def test_allowed_ip_serves_docs(self, client, set_allowlist, path):
        set_allowlist("203.0.113.5")
        resp = client.get(path, headers={"X-Forwarded-For": "203.0.113.5"})
        assert resp.status_code == 200

    @pytest.mark.parametrize("path", DOC_PATHS)
    def test_disallowed_ip_gets_404(self, client, set_allowlist, path):
        set_allowlist("203.0.113.5")
        resp = client.get(path, headers={"X-Forwarded-For": "198.51.100.9"})
        assert resp.status_code == 404

    @pytest.mark.parametrize("path", DOC_PATHS)
    def test_cidr_match(self, client, set_allowlist, path):
        set_allowlist("10.0.0.0/8")
        assert (
            client.get(path, headers={"X-Forwarded-For": "10.1.2.3"}).status_code == 200
        )
        assert (
            client.get(path, headers={"X-Forwarded-For": "11.0.0.1"}).status_code == 404
        )

    def test_ipv6_cidr_match(self, client, set_allowlist):
        set_allowlist("2001:db8::/32")
        ok = client.get("/openapi.json", headers={"X-Forwarded-For": "2001:db8::1"})
        no = client.get("/openapi.json", headers={"X-Forwarded-For": "2001:dead::1"})
        assert ok.status_code == 200
        assert no.status_code == 404

    def test_openapi_returns_valid_schema_when_allowed(self, client, set_allowlist):
        set_allowlist("203.0.113.5")
        resp = client.get("/openapi.json", headers={"X-Forwarded-For": "203.0.113.5"})
        assert resp.json()["info"]["title"]


class TestDocsAccessTrustProxyDisabled:
    @pytest.mark.parametrize("path", DOC_PATHS)
    def test_xff_ignored_when_trust_proxy_off(
        self, monkeypatch, client, set_allowlist, path
    ):
        # XFF must NOT be honored by default; the socket peer (testclient) is
        # used instead, which is not in the allowlist -> 404.
        monkeypatch.setattr(config.settings, "DOCS_TRUST_PROXY", False)
        set_allowlist("203.0.113.5")
        resp = client.get(path, headers={"X-Forwarded-For": "203.0.113.5"})
        assert resp.status_code == 404

    @pytest.mark.parametrize("path", DOC_PATHS)
    def test_socket_peer_allowed(self, monkeypatch, set_allowlist, path):
        monkeypatch.setattr(config.settings, "DOCS_TRUST_PROXY", False)
        set_allowlist("127.0.0.1")
        # TestClient's client host defaults to "testclient"; pin it to a real IP.
        local_client = TestClient(
            app, raise_server_exceptions=False, client=("127.0.0.1", 12345)
        )
        assert local_client.get(path).status_code == 200


def test_empty_allowlist_falls_back_to_localhost_only():
    """An empty DOCS_ALLOWED_HOSTS narrows to loopback, never allow-all."""
    nets = parse_ip_networks("")
    if not nets:
        nets = parse_ip_networks("127.0.0.1,::1")
    rendered = {str(n) for n in nets}
    assert rendered == {"127.0.0.1/32", "::1/128"}
