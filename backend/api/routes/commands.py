import time
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.commands.schemas import CommandRequest, CommandResult
from backend.brain.decider import brain_decider
from backend.commands.obs_adapter import obs_bridge

from backend.database.session import SessionLocal
from backend.database.models.command import Command as CommandModel
from backend.database.models.agent_command import AgentCommand
from backend.core.agent_bus import agent_bus
from backend.core.signing import sign_payload

router = APIRouter()
_service = None


def _decision_get(decision, key: str, default=None):
    if isinstance(decision, dict):
        return decision.get(key, default)
    return getattr(decision, key, default)


def _decision_scene(decision):
    payload = _decision_get(decision, "payload", {}) or {}
    if isinstance(payload, dict):
        return payload.get("scene")
    return None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------
# Service injection (called from main.py)
# --------------------------------------------------
def init_command_service(service):
    global _service
    _service = service


# --------------------------------------------------
# Direct executor endpoint (non-brain)
# --------------------------------------------------
@router.post("/execute", response_model=CommandResult)
async def execute_command(cmd: CommandRequest):
    if _service is None:
        raise RuntimeError("CommandService not initialized")

    return await _service.handle(cmd)


# --------------------------------------------------
# Voice adapter endpoint (Brain → Service)
# --------------------------------------------------
class VoiceCommandRequest(BaseModel):
    command: str


@router.post("/voice-command")
async def voice_command(payload: VoiceCommandRequest):
    if _service is None:
        return {"success": False, "error": "CommandService not initialized"}

    # Brain decides first
    live_scenes = await obs_bridge.get_all_scene_names()

    decision = brain_decider.decide(payload.command, live_scenes)
    intent = _decision_get(decision, "intent", "unknown")

    if intent == "unknown":
        return {
            "success": False,
            "intent": "unknown",
            "confidence": _decision_get(decision, "confidence", 0.0),
            "error": "Command not understood",
        }

    metadata = {}
    decision_payload = _decision_get(decision, "payload", {}) or {}
    if isinstance(decision_payload, dict):
        metadata.update(decision_payload)
    if intent == "switch_scene" and "scene" not in metadata:
        metadata["scene"] = _decision_scene(decision)

    cmd = CommandRequest(
        text=intent,          # 🔥 CRITICAL FIX
        metadata=metadata,
        is_brain=True,
        is_canonical=True,
    )

    try:
        result = await _service.handle(cmd)

        return {
            "success": result.status == "ok",
            "intent": intent,
            "decision": "execute",
            "confidence": _decision_get(decision, "confidence", 0.0),
            "result": {
                "status": result.status,
                "message": result.message,
                "data": result.data,
            },
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# --------------------------------------------------
# Phase B — Brain-powered PROCESS endpoint (DEMO GOLD)
# --------------------------------------------------
class ProcessCommandRequest(BaseModel):
    command: str
    role: str | None = None
    use_ai: bool | None = None


@router.post("/process")
async def process_voice_command(request: ProcessCommandRequest):
    if _service is None:
        return {"resolved_intent": "error", "execution_status": "service_not_ready"}

    use_ai = bool(
        request.use_ai
        or os.getenv("USE_GROQ_BRAIN", "false").lower() == "true"
    )
    if use_ai:
        ai_result = await _service.handle(
            CommandRequest(text=request.command, is_brain=True)
        )
        if isinstance(ai_result, dict):
            action = ai_result.get("action") or ai_result.get("intent") or "unknown"
            exec_result = ai_result.get("result")
            exec_status = getattr(exec_result, "status", None) if exec_result else None
            execution_status = (
                "success" if exec_status == "ok" else ("no_action" if not exec_result else "error")
            )
            commentary = ai_result.get("commentary") or ai_result.get("error") or ""
            return {
                "resolved_intent": action,
                "execution_status": execution_status,
                "director_commentary": commentary,
                "message": commentary,
            }

    # 1. Fetch real OBS scenes
    live_scenes = await obs_bridge.get_all_scene_names()

    # 2. Brain decides (pure logic)
    decision = brain_decider.decide(request.command, live_scenes)
    intent = _decision_get(decision, "intent", "unknown")

    if intent == "unknown":
        return {"resolved_intent": "unknown", "execution_status": "no_action", "message": "Command not understood"}

    # --- OUR NEW PERMISSION GUARD ---
    # We define what a viewer is ALLOWED to trigger automatically
    safe_intents = ["list_scenes", "get_status", "get_available_sources", "get_available_cameras"]

    if intent not in safe_intents:
        # Instead of executing, we log it for the streamer's dashboard
        from backend.main import event_log, _enqueue_command
        
        event_log.append({
            "time": time.time(),
            "type": "viewer_suggestion",
            "description": f"Viewer requested: {_decision_scene(decision) or 'Unknown Scene'}",
            "commentary": f"AI identified intent as '{intent}' from input '{request.command}'",
            "status": "pending_approval"
        })
        _enqueue_command(request.command)

        return {
            "resolved_intent": intent,
            "execution_status": "pending_approval",
            "director_commentary": "I've passed your request to the streamer for approval.",
            "message": "I've passed your request to the streamer for approval.",
        }

    # 3. If it's safe or not a protected intent, proceed with execution
    # Special handling for list_scenes - return scenes without executing OBS actions
    if intent == "list_scenes":
        return {
            "resolved_intent": "list_scenes",
            "execution_status": "success",
            "director_commentary": ", ".join(live_scenes),
            "message": ", ".join(live_scenes),
        }

    # 2. Build canonical executor command
    metadata = {}
    decision_payload = _decision_get(decision, "payload", {}) or {}
    if isinstance(decision_payload, dict):
        metadata.update(decision_payload)
    if intent == "switch_scene" and "scene" not in metadata:
        metadata["scene"] = _decision_scene(decision)

    cmd = CommandRequest(
        text=intent,          # 🔥 FIX: canonical command
        metadata=metadata,
        is_brain=False,
        is_canonical=True,
    )

    try:
        result = await _service.handle(cmd)

        execution_status = (
            "success" if result.status == "ok" else "error"
        )

        commentary = result.message or ""

    except Exception as e:
        return {
            "resolved_intent": intent,
            "execution_status": "error",
            "director_commentary": str(e),
        }

    # 3. Log event (demo visibility)
    from backend.main import event_log

    event_log.append(
        {
            "time": time.time(),
            "action": intent,
            "reason": commentary or "N/A",
        }
    )

    # 4. Clean investor-ready response
    return {
        "resolved_intent": intent,
        "execution_status": execution_status,
        "director_commentary": commentary,
        "message": commentary,
    }

@router.patch("/{command_id}/status")
async def update_command_status(
    command_id: int, 
    status_update: dict, 
    db: Session = Depends(get_db)
):
    # 1. Find the command in the DB
    cmd_record = db.query(CommandModel).filter(CommandModel.id == command_id).first()
    
    if not cmd_record:
        raise HTTPException(status_code=404, detail="Command not found")

    # 2. Update the status (approved or rejected)
    new_status = status_update.get("status")
    cmd_record.status = new_status
    db.commit()

    # 3. If APPROVED, trigger the execution logic
    if new_status == "approved":
        if cmd_record.streamer_id:
            action_payload = {}
            if cmd_record.intent == "switch_scene":
                action_payload = {"scene": cmd_record.command_text.split(":")[-1].strip()}
            agent_cmd = AgentCommand(
                streamer_id=cmd_record.streamer_id,
                command_id=cmd_record.id,
                action=cmd_record.intent,
                payload=action_payload,
                status="pending",
            )
            db.add(agent_cmd)
            db.commit()
            payload = {
                "id": agent_cmd.id,
                "streamer_id": agent_cmd.streamer_id,
                "command_id": agent_cmd.command_id,
                "action": agent_cmd.action,
                "payload": agent_cmd.payload or {},
                "created_at": agent_cmd.created_at.isoformat() if agent_cmd.created_at else "",
            }
            signature = sign_payload(payload)
            try:
                await agent_bus.send(agent_cmd.streamer_id, {"command": payload, "signature": signature})
            except Exception:
                pass

        use_local_agent = os.getenv("USE_LOCAL_AGENT", "false").lower() == "true"
        if use_local_agent:
            return {"status": "queued_for_agent"}

        if _service is None:
            return {"status": "approved_in_db", "error": "CommandService not ready for execution"}

        print(f"?? Executing approved command: {cmd_record.intent}")

        # Prepare the request for your existing executor
        execution_req = CommandRequest(
            text=cmd_record.intent,
            metadata={"scene": cmd_record.command_text.split(":")[-1].strip()}, # Extract scene if switch
            is_brain=True,
            is_canonical=True
        )

        # This actually moves OBS!
        await _service.handle(execution_req)

    return {"status": "success", "new_state": new_status}


# --------------------------------------------------
# IPC — Trigger listen (unchanged)
# --------------------------------------------------
@router.post("/trigger_listen")
async def trigger_listen():
    """Creates a wake signal file that the voice service detects."""

    import os

    signal_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "wake_signal.tmp",
    )

    try:
        with open(signal_file, "w") as f:
            f.write(str(time.time()))

        return {
            "status": "success",
            "message": "Listen signal sent to voice service",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }
