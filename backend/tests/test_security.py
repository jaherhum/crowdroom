from backend.core.config import settings
from backend.core.security import SecurityService
from backend.db.models.enum import TokenType


def test_security():
    """
    Manual test to verify the integrity of the SecurityService.
    Covers password hashing, token generation, and JWT decoding.
    """
    service = SecurityService(settings)

    # Test hashing
    password = "ILoveTL0Zbtw-!"
    hashed = service.get_password_hash(password)
    print(f"Generated hash: {hashed}")
    assert service.verify_password(password, hashed) is True
    assert service.verify_password("IHateTL0Zbtw-!", hashed) is False
    print("Hashing verified.")

    # Test Generate JWT
    payload = {"sub": "hello@jaherhum.dev"}
    token = service.create_token(TokenType.ACCESS, payload)
    print(f"Generated token: {token}")
    assert isinstance(token, str)

    # Test decode JWT
    decoded = service.decode_token(token)
    assert decoded["sub"] == "hello@jaherhum.dev"
    print("JWT Decoded & Verified.")


if __name__ == "__main__":
    try:
        test_security()
        print("\nTests passed successfully.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()