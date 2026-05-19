"""Tests for encryption utility functions."""

# ruff: noqa: D101, D102
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

with patch("backend.core.config.settings") as mock_settings:
    mock_settings.ENCRYPTION_KEY = Fernet.generate_key().decode()
    from backend.core.encryption import decrypt_data, encrypt_data


class TestEncryption:
    def test_encrypt_returns_string(self):
        result = encrypt_data({"client_id": "abc", "client_secret": "xyz"})
        assert isinstance(result, str)

    def test_encrypt_decrypt_roundtrip(self):
        original = {"client_id": "my_id", "client_secret": "my_secret"}
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        assert decrypted == original

    def test_encrypted_value_differs_from_plaintext(self):
        data = {"client_id": "abc"}
        encrypted = encrypt_data(data)
        assert "abc" not in encrypted

    def test_decrypt_empty_dict(self):
        encrypted = encrypt_data({})
        assert decrypt_data(encrypted) == {}

    def test_decrypt_invalid_token_raises(self):
        with pytest.raises(Exception):
            decrypt_data("not-a-valid-fernet-token")
