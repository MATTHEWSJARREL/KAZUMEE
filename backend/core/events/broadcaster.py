import json
from backend.api.websockets import manager as ws_manager

class Broadcaster:
    async def notify_ui(self, message_type: str, data: dict):
        payload = {
            "type": message_type,
            "payload": data
        }
        await ws_manager.broadcast(payload)

broadcaster = Broadcaster()
