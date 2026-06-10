"""WebSocket communication routes with ping/pong heartbeat."""

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.config import settings

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and room-based broadcasting."""

    def __init__(self) -> None:
        """Initialize the ConnectionManager with empty connection state.

        Creates an internal mapping of room_id to sets of active WebSocket
        connections, populated lazily as clients connect.
        """
        self.active_connections: dict[str, set[WebSocket]] = {}
        self._last_pong: dict[WebSocket, float] = {}

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        """Accept and register a new WebSocket connection for a room.

        Args:
            websocket: The WebSocket connection to accept.
            room_id: The identifier of the room to join.
        """
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)
        self._last_pong[websocket] = time.monotonic()

    async def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        """Remove a WebSocket connection from its room.

        Args:
            websocket: The WebSocket connection to remove.
            room_id: The identifier of the room to leave.
        """
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        self._last_pong.pop(websocket, None)

    def record_pong(self, websocket: WebSocket) -> None:
        """Record that a pong was received from this connection.

        Args:
            websocket: The WebSocket connection that sent the pong.
        """
        self._last_pong[websocket] = time.monotonic()

    def is_stale(self, websocket: WebSocket) -> bool:
        """Check if a connection has missed its pong deadline.

        Args:
            websocket: The WebSocket connection to check.

        Returns:
            True if the connection has not responded within the allowed window.
        """
        last = self._last_pong.get(websocket)
        if last is None:
            return True
        elapsed = time.monotonic() - last
        timeout = (
            settings.WS_HEARTBEAT_INTERVAL_SECONDS
            + settings.WS_HEARTBEAT_TIMEOUT_SECONDS
        )
        return elapsed > timeout

    async def broadcast(self, message: dict[str, Any], room_id: str) -> None:
        """Send a message to every WebSocket client in a room.

        Args:
            message: A dictionary containing the message payload to send.
            room_id: The identifier of the room to broadcast to.
        """
        if room_id in self.active_connections:
            connections = list(self.active_connections[room_id])
            tasks = [
                self._safe_send(connection, message, room_id)
                for connection in connections
            ]
            if tasks:
                await asyncio.gather(*tasks)

    async def _safe_send(
        self, connection: WebSocket, message: dict[str, Any], room_id: str
    ) -> None:
        """Send a JSON message to a single WebSocket connection.

        Removes the connection on failure to prevent repeated broadcast
        attempts to stale connections.

        Args:
            connection: The WebSocket connection to send to.
            message: A dictionary containing the message payload to send.
            room_id: The room the connection belongs to.
        """
        try:
            await connection.send_json(message)
        except Exception:
            await self.disconnect(connection, room_id)


manager = ConnectionManager()


async def _receive_loop(websocket: WebSocket, room_id: str) -> None:
    """Listen for client messages and handle pong replies.

    Args:
        websocket: The WebSocket connection to listen on.
        room_id: The identifier of the room the client is in.
    """
    while True:
        data = await websocket.receive_text()
        try:
            msg = json.loads(data)
            if isinstance(msg, dict) and msg.get("type") == "pong":
                manager.record_pong(websocket)
        except json.JSONDecodeError, AttributeError:
            pass


async def _heartbeat_loop(websocket: WebSocket, room_id: str) -> None:
    """Periodically send ping and close stale connections.

    Args:
        websocket: The WebSocket connection to ping.
        room_id: The identifier of the room the client is in.
    """
    interval = settings.WS_HEARTBEAT_INTERVAL_SECONDS
    while True:
        await asyncio.sleep(interval)
        if manager.is_stale(websocket):
            await websocket.close(code=1008, reason="heartbeat timeout")
            return
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            return


@router.websocket("/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    """Accept client WebSocket connections with heartbeat monitoring.

    Spawns a receive loop and a heartbeat loop as concurrent tasks.
    When either task ends (disconnect or heartbeat timeout), the
    connection is cleaned up.

    Args:
        websocket: The incoming WebSocket connection.
        room_id: The identifier of the room to join.
    """
    await manager.connect(websocket, room_id)
    try:
        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(_receive_loop(websocket, room_id))
            task_group.create_task(_heartbeat_loop(websocket, room_id))
    except* WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, room_id)
