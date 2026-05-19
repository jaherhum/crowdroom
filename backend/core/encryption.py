"""Encryption system services for the application."""

import json

from cryptography.fernet import Fernet

from backend.core.config import settings

_fernet = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_data(data: dict) -> str:
    json_str = json.dumps(data)
    json_bytes = json_str.encode()
    encrypted_bytes = _fernet.encrypt(json_bytes)
    return encrypted_bytes.decode()

def decrypt_data(data: str) -> dict:
    str_bytes = data.encode()
    decrypted_bytes = _fernet.decrypt(str_bytes)
    return json.loads(decrypted_bytes)
