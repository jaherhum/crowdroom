"""Encryption system services for the application."""

import json

from cryptography.fernet import Fernet

from backend.core.config import settings

_fernet = Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_data(data: dict) -> str:
    """Encrypt a dictionary to a Fernet-encoded string.

    Args:
        data: Plain dictionary to encrypt.

    Returns:
        Base64-encoded encrypted string.
    """
    json_str = json.dumps(data)
    json_bytes = json_str.encode()
    encrypted_bytes = _fernet.encrypt(json_bytes)
    return encrypted_bytes.decode()


def decrypt_data(data: str) -> dict:
    """Decrypt a Fernet-encoded string back to a dictionary.

    Args:
        data: Encrypted string produced by ``encrypt_data``.

    Returns:
        Original dictionary.
    """
    str_bytes = data.encode()
    decrypted_bytes = _fernet.decrypt(str_bytes)
    return json.loads(decrypted_bytes)


def decrypt_data_with_ttl(data: str, ttl_seconds: int) -> dict:
    """Decrypt a Fernet-encoded string, rejecting tokens older than ttl_seconds.

    Args:
        data: Encrypted string produced by ``encrypt_data``.
        ttl_seconds: Maximum allowed age of the token in seconds.

    Returns:
        Original dictionary.

    Raises:
        cryptography.fernet.InvalidToken: If token is expired or tampered.
    """
    str_bytes = data.encode()
    decrypted_bytes = _fernet.decrypt(str_bytes, ttl=ttl_seconds)
    return json.loads(decrypted_bytes)
