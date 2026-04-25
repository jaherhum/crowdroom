"""WebSocket communication routes for the API."""

from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and room-based broadcasting."""

    def __init__(self) -> None:
        # Maps room_id (str) -> set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        """Accepts a connection and adds it to a specific room."""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        """Removes a connection from a specific room."""
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            # Clean up the room if no connections are left
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: dict, room_id: str) -> None:
        """Sends a JSON message to all connections in a specific room."""
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
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