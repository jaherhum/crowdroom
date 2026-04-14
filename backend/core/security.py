from datetime import timedelta, timezone, datetime

import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel

from backend.core.config import Settings
from backend.db.models.enum import TokenType


class SecurityService:
    """
    Service responsible for JWT token lifecycle management
    and secure password hashing.
    """
    def __init__(self, settings: Settings):
        """
        Initializes the security service with system-wide security configurations.

        Args:
            settings (Settings): Global application settings containing security parameters.
        """
        self._secret_key = settings.SECRET_KEY
        self._algorithm = settings.ALGORITHM
        self._access_expire_min = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self._refresh_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
        self._pass_hash = PasswordHash.recommended()

    def create_token(self, token_type: TokenType, data: dict) -> str:
        """
        Generates a signed JWT (Access or Refresh token) with a calculated expiration.

        Args:
            token_type (TokenType): The category of token to be issued.
            data (dict): Payload data to encode. Must contain the "sub" (subject) key.

        Returns:
            str: The encoded JWT string.

        Raises:
            ValueError: If the "sub" key is missing or an invalid token type is provided.
        """
        if data.get("sub") is None:
            raise ValueError("Missing sub")

        to_encode = data.copy()

        if token_type == TokenType.REFRESH:
            expire = datetime.now(timezone.utc) + timedelta(days=self._refresh_expire_days)
        elif token_type == TokenType.ACCESS:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self._access_expire_min)
        else:
            raise ValueError(f"Unknown token type: {token_type}")

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)
        return encoded_jwt

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verifies a plain-text password against its stored hash.

        Args:
            password (str): The plain-text password to verify.
            hashed_password (str): The secure hash to compare against.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return self._pass_hash.verify(password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Generates a secure hash for a plain-text password.

        Args:
            password (str): The plain-text password to hash.

        Returns:
            str: The generated secure hash.
        """
        return self._pass_hash.hash(password)

    def decode_token(self, token: str) -> dict:
        """
        Decodes and validates a JWT, ensuring signature integrity and expiration.

        Args:
            token (str): The JWT string to decode.

        Returns:
            dict: The decoded payload.

        Raises:
            jwt.exceptions.DecodeError: If the token is invalid, tampered with, or expired.
        """
        return jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
