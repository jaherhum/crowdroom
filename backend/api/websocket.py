"""WebSocket communication routes for the API."""

from typing import Any, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and room-based broadcasting."""

    def __init__(self) -> None:
        """Initialize the ConnectionManager with empty connection state.

        Creates an internal mapping of room_id to sets of active WebSocket
        connections, populated lazily as clients connect.
        """
        # Maps room_id (str) -> set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(
        self, websocket: WebSocket, room_id: str
    ) -> None:
        """Accept and register a new WebSocket connection for a room.

        Accepts the WebSocket upgrade handshake and adds the connection
        to the room's active connections set.

        Args:
            websocket: The WebSocket connection to accept.
            room_id: The identifier of the room to join.
        """
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)

    async def disconnect(
        self, websocket: WebSocket, room_id: str
    ) -> None:
        """Remove a WebSocket connection from its room.

        Removes the connection from the room's active set and cleans up
        the room entry if no connections remain.

        Args:
            websocket: The WebSocket connection to remove.
            room_id: The identifier of the room to leave.
        """
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(
        self, message: Dict[str, Any], room_id: str
    ) -> None:
        """Send a message to every WebSocket client in a room.

        Iterates over all active connections for the given room and sends
        the message in parallel using asyncio.gather.

        Args:
            message: A dictionary containing the message payload to send.
            room_id: The identifier of the room to broadcast to.
        """
        if room_id in self.active_connections:
            # Create a list of tasks to send messages in parallel
            import asyncio

            connections = list(self.active_connections[room_id])
            tasks = []
            for connection in connections:
                tasks.append(self._safe_send(connection, message))
            if tasks:
                await asyncio.gather(*tasks)

    async def _safe_send(
        self, connection: WebSocket, message: Dict[str, Any]
    ) -> None:
        """Send a JSON message to a single WebSocket connection.

        Silently catches and swallows any exceptions that occur during send,
        allowing the broadcast loop to continue even if some connections are
        stale or closed.

        Args:
            connection: The WebSocket connection to send to.
            message: A dictionary containing the message payload to send.
        """
        try:
            await connection.send_json(message)
        except Exception:
            # Handle stale connections that might have closed without disconnect()
            pass


manager = ConnectionManager()


@router.websocket("/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    """Accept client WebSocket connections and relay messages within a room.

    Accepts the connection, keeps it alive, and listens for incoming text
    messages from clients. When the client disconnects, cleans up the
    connection registration.

    Args:
        websocket: The incoming WebSocket connection.
        room_id: The identifier of the room to join.
    """
    await manager.connect(websocket, room_id)
    try:
        while True:
            # Keep the connection alive and listen for any client messages if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
