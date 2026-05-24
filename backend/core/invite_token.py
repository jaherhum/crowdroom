import secrets
import string

INVITE_TOKEN_CHARSET = string.ascii_letters + string.digits
INVITE_TOKEN_LENGTH = 12

def generate_invite_token() -> str:
    return "".join(secrets.choice(INVITE_TOKEN_CHARSET) for _ in range(INVITE_TOKEN_LENGTH))