from fastapi import Depends
from backend.api.users.dependencies import get_user_service
from backend.services.auth_service import AuthService
from backend.services.user_service import UserService
from backend.core.security import SecurityService


def get_security_service() -> SecurityService:
    from backend.core.config import settings
    return SecurityService(settings)


def get_auth_service(user_service: UserService = Depends(get_user_service), security_service: SecurityService = Depends(get_security_service),) -> AuthService:
    return AuthService(user_service, security_service)
