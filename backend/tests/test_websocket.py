"""Integration tests for WebSocket endpoint, auth, and event broadcasting."""

# ruff: noqa: D101, D102, D103

from uuid import UUID, uuid4

import anyio
import pytest
from fastapi import WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.api.users.dependencies import get_user_service
from backend.api.websocket import authenticate_ws_connection, manager
from backend.core.config import settings
from backend.core.security import SecurityService
from backend.db.models.enum import TokenType
from backend.db.models.user import User
from backend.main import app


def _make_member(room_id: str) -> User:
    """Build a User who is a member of the given room."""
    return User(id=uuid4(), username=f"u{uuid4().hex[:8]}", room_id=UUID(room_id))


def _override_authorized_user(room_id: str) -> User:
    """Override the WS auth dependency so any handshake is authorized."""
    user = _make_member(room_id)
    app.dependency_overrides[authenticate_ws_connection] = lambda: user
    return user


class _FakeUserService:
    """Minimal stand-in for UserService.get_by_id used by WS auth tests."""

    def __init__(self, users: dict[UUID, User]):
        self._users = users

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)


def _access_token(user_id: UUID) -> str:
    return SecurityService(settings).create_token(
        TokenType.ACCESS, {"sub": str(user_id)}
    )


class TestWebSocketAuth:
    """Exercises the real authenticate_ws_connection dependency."""

    @pytest.fixture
    def client(self):
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def test_connection_without_cookie_is_rejected(self, client):
        room_id = str(uuid4())
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/{room_id}"):
                pass
        assert exc.value.code == 1008
        assert room_id not in manager.active_connections

    def test_connection_with_invalid_token_is_rejected(self, client):
        room_id = str(uuid4())
        client.cookies.set(settings.AUTH_COOKIE_NAME, "not-a-jwt")
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/{room_id}"):
                pass
        assert exc.value.code == 1008
        assert room_id not in manager.active_connections

    def test_non_member_is_rejected(self, client):
        room_id = str(uuid4())
        # Valid token + existing user, but they belong to a different room.
        non_member = User(id=uuid4(), username="outsider", room_id=uuid4())
        app.dependency_overrides[get_user_service] = lambda: _FakeUserService(
            {non_member.id: non_member}
        )
        client.cookies.set(settings.AUTH_COOKIE_NAME, _access_token(non_member.id))
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/{room_id}"):
                pass
        assert exc.value.code == 1008
        assert room_id not in manager.active_connections

    def test_member_connects_successfully(self, client):
        room_id = str(uuid4())
        member = _make_member(room_id)
        app.dependency_overrides[get_user_service] = lambda: _FakeUserService(
            {member.id: member}
        )
        client.cookies.set(settings.AUTH_COOKIE_NAME, _access_token(member.id))
        with client.websocket_connect(f"/ws/{room_id}"):
            assert room_id in manager.active_connections
            assert len(manager.active_connections[room_id]) == 1


class TestWebSocketConnect:
    @pytest.fixture
    def client(self):
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def test_client_connects_successfully(self, client):
        room_id = str(uuid4())
        _override_authorized_user(room_id)
        with client.websocket_connect(f"/ws/{room_id}"):
            assert room_id in manager.active_connections
            assert len(manager.active_connections[room_id]) == 1

    def test_disconnect_cleans_up_connection(self, client):
        room_id = str(uuid4())
        _override_authorized_user(room_id)
        with client.websocket_connect(f"/ws/{room_id}"):
            pass
        assert room_id not in manager.active_connections


class TestWebSocketBroadcast:
    @pytest.fixture
    def client(self):
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def test_client_receives_member_joined(self, client):
        room_id = str(uuid4())
        _override_authorized_user(room_id)
        with client.websocket_connect(f"/ws/{room_id}") as websocket:
            message = {
                "type": "member_joined",
                "room_id": room_id,
                "user_id": str(uuid4()),
                "username": "newuser",
            }

            async def broadcast():
                await manager.broadcast(message, room_id)

            anyio.run(broadcast)
            data = websocket.receive_json()
            assert data["type"] == "member_joined"
            assert data["username"] == "newuser"

    def test_client_receives_queue_updated(self, client):
        room_id = str(uuid4())
        _override_authorized_user(room_id)
        with client.websocket_connect(f"/ws/{room_id}") as websocket:
            message = {
                "type": "queue_updated",
                "action": "added",
                "room_id": room_id,
                "queue": [{"song_id": str(uuid4()), "title": "Test Song"}],
            }

            async def broadcast():
                await manager.broadcast(message, room_id)

            anyio.run(broadcast)
            data = websocket.receive_json()
            assert data["type"] == "queue_updated"
            assert data["action"] == "added"
            assert len(data["queue"]) == 1

    def test_client_receives_song_changed(self, client):
        room_id = str(uuid4())
        _override_authorized_user(room_id)
        with client.websocket_connect(f"/ws/{room_id}") as websocket:
            message = {
                "type": "song_changed",
                "room_id": room_id,
                "song": {"title": "Next Song", "artist": "Artist"},
            }

            async def broadcast():
                await manager.broadcast(message, room_id)

            anyio.run(broadcast)
            data = websocket.receive_json()
            assert data["type"] == "song_changed"
            assert data["song"]["title"] == "Next Song"

    def test_client_receives_skip_vote(self, client):
        room_id = str(uuid4())
        _override_authorized_user(room_id)
        with client.websocket_connect(f"/ws/{room_id}") as websocket:
            message = {
                "type": "skip_vote",
                "room_id": room_id,
                "queue_item_id": str(uuid4()),
                "voter_id": str(uuid4()),
                "current_votes": 2,
                "threshold": 3,
                "skip_triggered": False,
            }

            async def broadcast():
                await manager.broadcast(message, room_id)

            anyio.run(broadcast)
            data = websocket.receive_json()
            assert data["type"] == "skip_vote"
            assert data["current_votes"] == 2
            assert data["skip_triggered"] is False

    def test_disconnect_no_error_on_next_broadcast(self, client):
        room_id = str(uuid4())
        _override_authorized_user(room_id)
        with client.websocket_connect(f"/ws/{room_id}"):
            pass

        async def broadcast():
            await manager.broadcast({"type": "test"}, room_id)

        anyio.run(broadcast)


class TestWebSocketMultiClient:
    @pytest.fixture
    def client(self):
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def test_multiple_clients_same_room_all_receive(self, client):
        room_id = str(uuid4())
        _override_authorized_user(room_id)
        with client.websocket_connect(f"/ws/{room_id}") as websocket_one:
            with client.websocket_connect(f"/ws/{room_id}") as websocket_two:
                assert len(manager.active_connections[room_id]) == 2

                message = {
                    "type": "member_joined",
                    "room_id": room_id,
                    "user_id": str(uuid4()),
                    "username": "third_user",
                }

                async def broadcast():
                    await manager.broadcast(message, room_id)

                anyio.run(broadcast)
                data_one = websocket_one.receive_json()
                data_two = websocket_two.receive_json()
                assert data_one["type"] == "member_joined"
                assert data_two["type"] == "member_joined"
                assert data_one["username"] == "third_user"
                assert data_two["username"] == "third_user"

    def test_client_in_different_room_does_not_receive(self, client):
        room_a = str(uuid4())
        room_b = str(uuid4())
        # Authorize both rooms regardless of which path is requested.
        member_a = _make_member(room_a)
        member_b = _make_member(room_b)

        def _auth(websocket: WebSocket, room_id: str) -> User:
            return member_a if room_id == room_a else member_b

        app.dependency_overrides[authenticate_ws_connection] = _auth
        with client.websocket_connect(f"/ws/{room_a}") as websocket_a:
            with client.websocket_connect(f"/ws/{room_b}") as websocket_b:

                async def broadcast():
                    await manager.broadcast(
                        {"type": "for_room_a_only", "data": "secret"}, room_a
                    )
                    await manager.broadcast({"type": "sentinel"}, room_b)

                anyio.run(broadcast)

                data_a = websocket_a.receive_json()
                assert data_a["type"] == "for_room_a_only"

                data_b = websocket_b.receive_json()
                assert data_b["type"] == "sentinel"
