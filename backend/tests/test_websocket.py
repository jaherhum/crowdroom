"""Integration tests for WebSocket endpoint and event broadcasting."""

# ruff: noqa: D101, D102, D103

from uuid import uuid4

import anyio
import pytest
from fastapi.testclient import TestClient

from backend.api.websocket import manager
from backend.main import app


class TestWebSocketConnect:
    @pytest.fixture
    def client(self):
        with TestClient(app) as test_client:
            yield test_client

    def test_client_connects_successfully(self, client):
        room_id = str(uuid4())
        with client.websocket_connect(f"/ws/{room_id}"):
            assert room_id in manager.active_connections
            assert len(manager.active_connections[room_id]) == 1

    def test_disconnect_cleans_up_connection(self, client):
        room_id = str(uuid4())
        with client.websocket_connect(f"/ws/{room_id}"):
            pass
        assert room_id not in manager.active_connections


class TestWebSocketBroadcast:
    @pytest.fixture
    def client(self):
        with TestClient(app) as test_client:
            yield test_client

    def test_client_receives_member_joined(self, client):
        room_id = str(uuid4())
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

    def test_multiple_clients_same_room_all_receive(self, client):
        room_id = str(uuid4())
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
