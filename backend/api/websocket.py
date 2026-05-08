"""WebSocket communication routes for the API."""

from typing import Any, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and room-based broadcasting."""

    def __init__(self) -> None:
        """Initialize the ConnectionManager."""
        # Maps room_id (str) -> set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        """Connect a new WebSocket to a room."""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        """Disconnect a WebSocket from a room."""
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: Dict[str, Any], room_id: str) -> None:
        """Broadcast a message to all connected clients in a room."""
        if room_id in self.active_connections:
            # Create a list of tasks to send messages in parallel
            import asyncio

            connections = list(self.active_connections[room_id])
            tasks = []
            for connection in connections:
                tasks.append(self._safe_send(connection, message))
            if tasks:
                await asyncio.gather(*tasks)

    async def _safe_send(self, connection: WebSocket, message: Dict[str, Any]) -> None:
        """Safely send a message to a single WebSocket connection."""
        try:
            await connection.send_json(message)
        except Exception:
            # Handle stale connections that might have closed without disconnect()
            pass


manager = ConnectionManager()


@router.websocket("/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    """WebSocket endpoint for clients to connect to a room."""
    await manager.connect(websocket, room_id)
    try:
        while True:
            # Keep the connection alive and listen for any client messages if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
