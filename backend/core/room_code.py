import secrets

CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
ROOM_CODE_LENGTH = 6

def generate_room_code() -> str:
    return "".join(secrets.choice(CHARSET) for _ in range(ROOM_CODE_LENGTH))