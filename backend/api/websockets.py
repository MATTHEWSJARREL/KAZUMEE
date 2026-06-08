from fastapi import WebSocket
from typing import List, Optional, Tuple
import json

class ConnectionManager:
    def __init__(self):
        # Store active connections
        self.active_connections: List[Tuple[WebSocket, Optional[int]]] = []

    async def connect(self, websocket: WebSocket, streamer_id: Optional[int] = None):
        await websocket.accept()
        self.active_connections.append((websocket, streamer_id))
        print(f"New connection! Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections = [
            (ws, sid) for (ws, sid) in self.active_connections if ws is not websocket
        ]

    async def broadcast(self, message):
        # Send message to EVERYONE connected
        target_streamer_id = None
        payload_text = message if isinstance(message, str) else json.dumps(message)
        if isinstance(message, dict) and message.get("streamer_id") is not None:
            try:
                target_streamer_id = int(message.get("streamer_id"))
            except Exception:
                target_streamer_id = None

        for connection, conn_streamer_id in self.active_connections:
            if target_streamer_id is not None and conn_streamer_id != target_streamer_id:
                continue
            try:
                await connection.send_text(payload_text)
            except Exception:
                # Clean up stale connections
                self.disconnect(connection)

manager = ConnectionManager()
