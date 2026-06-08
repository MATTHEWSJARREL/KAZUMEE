from typing import Dict, Set
from fastapi import WebSocket


class AgentBus:
    def __init__(self):
        self.connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, streamer_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(streamer_id, set()).add(websocket)

    def disconnect(self, streamer_id: int, websocket: WebSocket):
        if streamer_id in self.connections:
            self.connections[streamer_id].discard(websocket)
            if not self.connections[streamer_id]:
                self.connections.pop(streamer_id, None)

    async def send(self, streamer_id: int, payload: dict):
        sockets = list(self.connections.get(streamer_id, set()))
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(streamer_id, ws)


agent_bus = AgentBus()
