import base64
from typing import ClassVar

import httpx

from backend.core.exceptions import InvalidPlatformCredentialsException


class SpotifyAuthAdapter:
    @staticmethod
    async def validate_credentials(credentials: dict[str, str]) -> None:
        required = {"client_id", "client_secret"}
        missing = required - credentials.keys()
        if missing:
            raise InvalidPlatformCredentialsException(f"Missing keys: {missing}")

        client_id = credentials["client_id"]
        client_secret = credentials["client_secret"]

        authorization_str = f"{client_id}:{client_secret}"
        authorization_bytes = authorization_str.encode("utf-8")
        authorization_base64 = base64.b64encode(authorization_bytes).decode("utf-8")
        authorization_header = f"Basic {authorization_base64}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url="https://accounts.spotify.com/api/token",
                headers={"Authorization": authorization_header},
                data={"grant_type": "client_credentials"},
            )
            if response.status_code != 200:
                raise InvalidPlatformCredentialsException("Spotify authorization failed")
            return None