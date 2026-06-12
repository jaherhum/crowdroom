"""Regression tests for UserService.create_user return shape."""

# ruff: noqa: D101, D103
from unittest.mock import MagicMock

from backend.core.security import SecurityService
from backend.db.models.user import User
from backend.repositories.user_repo import UserRepository
from backend.schemas.user import UserCreate
from backend.services.user_service import UserService


def test_create_user_returns_user_model_with_token_version():
    repo = MagicMock(spec=UserRepository)
    repo.save.side_effect = lambda u: u

    sec = MagicMock(spec=SecurityService)
    sec.generate_password_hash.return_value = "hashed"

    svc = UserService(user_repo=repo, security_service=sec)
    result = svc.create_user(
        UserCreate(username="alice", email="a@b.com", password="longpassword123")
    )

    assert isinstance(result, User)
    assert result.token_version == 0
    assert result.username == "alice"
    assert result.email == "a@b.com"
    assert result.hashed_password == "hashed"


def test_create_user_passwordless_user():
    repo = MagicMock(spec=UserRepository)
    repo.save.side_effect = lambda u: u
    sec = MagicMock(spec=SecurityService)

    svc = UserService(user_repo=repo, security_service=sec)
    result = svc.create_user(UserCreate(username="bob", email=None, password=None))

    assert isinstance(result, User)
    assert result.hashed_password is None
    assert result.token_version == 0
