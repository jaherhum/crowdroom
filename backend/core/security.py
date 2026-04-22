"""Core security services for the application."""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from backend.core.config import Settings
from backend.db.models.enum import TokenType


class SecurityService:
    """Service for JWT token lifecycle management and secure password hashing.

    Attributes:
        _secret_key (str): The secret key used for signing tokens.
        _algorithm (str): The algorithm used for token signing.
        _access_expire_min (int): The expiration time for access tokens in minutes.
        _refresh_expire_days (int): The expiration time for refresh tokens in days.
        _pass_hash (PasswordHash): The password hashing utility.
    """

    def __init__(self, settings: Settings):
        """Initializes the security service.

        Args:
            settings (Settings): Global application settings.
        """
        self._secret_key = settings.SECRET_KEY
        self._algorithm = settings.ALGORITHM
        self._access_expire_min = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self._refresh_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
        self._pass_hash = PasswordHash.recommended()

    def create_token(self, token_type: TokenType, data: dict) -> str:
        """Generates a signed JWT with a calculated expiration.

        Args:
            token_type (TokenType): The category of token to be issued.
            data (dict): Payload data to encode. Must contain the "sub" key.

        Returns:
            str: The encoded JWT string.

        Raises:
            ValueError: If the "sub" key is missing or an invalid token type is
                provided.
        """
        if data.get("sub") is None:
            raise ValueError("Missing 'sub' claim in token data")

        to_encode = data.copy()

        if token_type == TokenType.REFRESH:
            expire = (
                datetime.now(timezone.utc) + timedelta(days=self._refresh_expire_days)
            )
        elif token_type == TokenType.ACCESS:
            expire = (
                datetime.now(timezone.utc) + timedelta(minutes=self._access_expire_min)
            )
        else:
            raise ValueError(f"Unknown token type: {token_type}")

        to_encode["type"] = token_type.value
        to_encode["iat"] = datetime.now(timezone.utc)
        to_encode["exp"] = expire

        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verifies a plain-text password against its stored hash.

        Args:
            password (str): The plain-text password to verify.
            hashed_password (str): The secure hash to compare against.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return self._pass_hash.verify(password, hashed_password)

    def generate_password_hash(self, password: str) -> str:
        """Generates a secure hash for a plain-text password.

        Args:
            password (str): The plain-text password to hash.

        Returns:
            str: The generated secure hash.
        """
        return self._pass_hash.hash(password)

    def decode_token(self, token: str, expected_type: TokenType | None = None) -> dict:
        """Decodes and validates a JWT.

        Args:
            token (str): The JWT string to decode.
            expected_type (TokenType | None): If provided, validates the token type.

        Returns:
            dict: The decoded payload.

        Raises:
            jwt.ExpiredSignatureError: If the token has expired.
            jwt.InvalidTokenError: If the token is malformed or invalid.
        """
        payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])

        if expected_type is not None and payload.get("type") != expected_type.value:
            raise jwt.InvalidTokenError(
                f"Expected '{expected_type.value}' token, got '{payload.get('type')}'"
            )

        return payload
