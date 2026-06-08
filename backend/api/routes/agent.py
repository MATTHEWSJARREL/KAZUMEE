from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
import os
from datetime import datetime

from backend.core.signing import sign_payload
from backend.core.agent_bus import agent_bus
from backend.database.session import SessionLocal
from backend.database.models.agent_command import AgentCommand
from backend.database.models.clip import Clip

router = APIRouter(prefix="/agent", tags=["Agent"])


def _require_agent_key(request: Request):
    expected = os.getenv("AGENT_ACCESS_KEY", "")
    provided = request.headers.get("X-Agent-Key", "")
    if not expected or provided != expected:
        raise HTTPException(status_code=401, detail="Invalid agent key")


def _require_agent_key_ws(websocket: WebSocket):
    expected = os.getenv("AGENT_ACCESS_KEY", "")
    provided = websocket.query_params.get("key", "")
    if not expected or provided != expected:
        return False
    return True


@router.websocket("/agent/ws")
async def agent_ws(websocket: WebSocket):
    if not _require_agent_key_ws(websocket):
        await websocket.close(code=1008)
        return
    streamer_id = websocket.query_params.get("streamer_id")
    if not streamer_id:
        await websocket.close(code=1008)
        return
    try:
        streamer_id_int = int(streamer_id)
    except ValueError:
        await websocket.close(code=1008)
        return

    await agent_bus.connect(streamer_id_int, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        agent_bus.disconnect(streamer_id_int, websocket)


@router.get("/commands/next")
async def get_next_command(request: Request, streamer_id: int | None = None):
    _require_agent_key(request)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    db = SessionLocal()
    try:
        cmd = (
            db.query(AgentCommand)
            .filter(AgentCommand.streamer_id == streamer_id, AgentCommand.status == "pending")
            .order_by(AgentCommand.created_at.asc())
            .first()
        )
        if not cmd:
            return {"status": "empty"}

        payload = {
            "id": cmd.id,
            "streamer_id": cmd.streamer_id,
            "command_id": cmd.command_id,
            "action": cmd.action,
            "payload": cmd.payload or {},
            "created_at": cmd.created_at.isoformat() if cmd.created_at else datetime.utcnow().isoformat(),
        }
        signature = sign_payload(payload)
        cmd.status = "sent"
        db.commit()
        return {"status": "ok", "command": payload, "signature": signature}
    finally:
        db.close()


@router.post("/commands/{command_id}/ack")
async def ack_command(request: Request, command_id: int, payload: dict):
    _require_agent_key(request)
    status = payload.get("status", "executed")
    message = payload.get("message")

    db = SessionLocal()
    try:
        cmd = db.query(AgentCommand).filter(AgentCommand.id == command_id).first()
        if not cmd:
            raise HTTPException(status_code=404, detail="Command not found")
        cmd.status = status
        if message:
            cmd.payload = {**(cmd.payload or {}), "agent_message": message}
        if cmd.action == "export_short_form":
            clip_id = (cmd.payload or {}).get("clip_id")
            if clip_id:
                clip = db.query(Clip).filter(Clip.id == clip_id).first()
                if clip:
                    clip.export_status = status
                    clip.export_updated_at = datetime.utcnow()
                    if cmd.payload.get("output_path"):
                        clip.export_path = cmd.payload.get("output_path")
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()
