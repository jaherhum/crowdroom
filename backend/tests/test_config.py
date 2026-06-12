"""Tests for application configuration validation."""

import logging
from unittest.mock import patch

from backend.core.config import validate_spotify_config


class TestValidateSpotifyConfig:
    def test_warns_when_client_id_missing(self, caplog):
        with patch("backend.core.config.settings") as mock_settings:
            mock_settings.SPOTIFY_CLIENT_ID = ""
            mock_settings.SPOTIFY_CLIENT_SECRET = "some-secret"
            with caplog.at_level(logging.WARNING):
                validate_spotify_config()
        assert "SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET not set" in caplog.text

    def test_warns_when_client_secret_missing(self, caplog):
        with patch("backend.core.config.settings") as mock_settings:
            mock_settings.SPOTIFY_CLIENT_ID = "some-id"
            mock_settings.SPOTIFY_CLIENT_SECRET = ""
            with caplog.at_level(logging.WARNING):
                validate_spotify_config()
        assert "SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET not set" in caplog.text

    def test_warns_when_redirect_uri_missing(self, caplog):
        with patch("backend.core.config.settings") as mock_settings:
            mock_settings.SPOTIFY_CLIENT_ID = "id"
            mock_settings.SPOTIFY_CLIENT_SECRET = "secret"
            mock_settings.SPOTIFY_REDIRECT_URI = ""
            with caplog.at_level(logging.WARNING):
                validate_spotify_config()
        assert "SPOTIFY_REDIRECT_URI not set" in caplog.text

    def test_no_warning_when_fully_configured(self, caplog):
        with patch("backend.core.config.settings") as mock_settings:
            mock_settings.SPOTIFY_CLIENT_ID = "id"
            mock_settings.SPOTIFY_CLIENT_SECRET = "secret"
            mock_settings.SPOTIFY_REDIRECT_URI = "http://localhost:8000/callback"
            with caplog.at_level(logging.WARNING):
                validate_spotify_config()
        assert caplog.text == ""

    def test_skips_redirect_check_when_credentials_missing(self, caplog):
        with patch("backend.core.config.settings") as mock_settings:
            mock_settings.SPOTIFY_CLIENT_ID = ""
            mock_settings.SPOTIFY_CLIENT_SECRET = ""
            mock_settings.SPOTIFY_REDIRECT_URI = ""
            with caplog.at_level(logging.WARNING):
                validate_spotify_config()
        assert "SPOTIFY_REDIRECT_URI not set" not in caplog.text
