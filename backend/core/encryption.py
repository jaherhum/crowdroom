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
