"""Tests for the global AppException -> HTTP status handlers in main.py."""

# ruff: noqa: D101, D102, D103
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api.rooms.dependencies import get_room_service
from backend.api.users.dependencies import get_user_repo
from backend.core.config import settings
from backend.core.exceptions import EntityNotFoundException
from backend.main import app
from backend.services.room_service import RoomService


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_get_members_returns_404_when_room_deleted(client):
    """A missing room must yield 404, not a generic 500.

    Regression test: get_room_members has no per-endpoint try/except, so it
    relies on the global EntityNotFoundException handler registered in main.py.
    """
    room_id = uuid4()

    mock_room_service = MagicMock(spec=RoomService)
    mock_room_service.get_room.side_effect = EntityNotFoundException("Room", room_id)

    app.dependency_overrides[get_room_service] = lambda: mock_room_service
    app.dependency_overrides[get_user_repo] = lambda: MagicMock()

    try:
        response = client.get(f"{settings.API_V1_STR}/rooms/{room_id}/members")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "detail" in response.json()
