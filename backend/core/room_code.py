"""Room code generation utility for shareable room discovery."""

import secrets

CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
ROOM_CODE_LENGTH = 6


def generate_room_code() -> str:
    """Generate a random 6-character room code from an unambiguous charset.

    Returns:
        A string of 6 uppercase alphanumeric characters excluding
        visually ambiguous characters (0, O, 1, I, L).
    """
    return "".join(secrets.choice(CHARSET) for _ in range(ROOM_CODE_LENGTH))
