from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.database.models.streamer import Streamer
from backend.database.session import get_db

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/voice-agent", tags=["VoiceAgent"])


class VoiceAgentStartRequest(BaseModel):
    trigger_word: str | None = None
    require_wake_word: bool = True
    use_ai: bool = True
    phrase_time_limit: int = Field(default=6, ge=2, le=12)
    ambient_adjust_seconds: float = Field(default=0.7, ge=0.1, le=3.0)
    command_timeout_seconds: int = Field(default=20, ge=3, le=45)


def _require_streamer(request: Request, db: Session) -> Streamer:
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return streamer


@router.get("/status")
def voice_agent_status(request: Request, db: Session = Depends(get_db)):
    _require_streamer(request, db)
    service = getattr(request.app.state, "voice_agent", None)
    if not service:
        return {
            "status": "error",
            "message": "Voice agent service not initialized",
            "available": False,
        }
    data = service.status()
    return {"status": "ok", **data}


@router.get("/logs")
def voice_agent_logs(request: Request, limit: int = 50, db: Session = Depends(get_db)):
    _require_streamer(request, db)
    service = getattr(request.app.state, "voice_agent", None)
    if not service:
        return {"status": "error", "logs": []}
    n = max(1, min(limit, 200))
    return {"status": "ok", "logs": service.get_logs(limit=n)}


@router.post("/start")
def start_voice_agent(payload: VoiceAgentStartRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    service = getattr(request.app.state, "voice_agent", None)
    if not service:
        raise HTTPException(status_code=503, detail="Voice agent service unavailable")

    settings_json = streamer.settings_json or {}
    voice_cfg = settings_json.get("voice") or {}
    trigger_word = (payload.trigger_word or voice_cfg.get("triggerWord") or "Kazumi").strip() or "Kazumi"

    result = service.start(
        trigger_word=trigger_word,
        require_wake_word=payload.require_wake_word,
        use_ai=payload.use_ai,
        streamer_id=streamer.id,
        phrase_time_limit=payload.phrase_time_limit,
        ambient_adjust_seconds=payload.ambient_adjust_seconds,
        command_timeout_seconds=payload.command_timeout_seconds,
    )
    if result.get("status") != "ok":
        raise HTTPException(status_code=400, detail=result.get("detail") or result.get("message") or "Failed to start voice agent")
    return {"status": "ok", "result": result}


@router.post("/stop")
def stop_voice_agent(request: Request, db: Session = Depends(get_db)):
    _require_streamer(request, db)
    service = getattr(request.app.state, "voice_agent", None)
    if not service:
        return {"status": "ok", "result": {"status": "ok", "message": "Voice agent service unavailable"}}
    result = service.stop()
    return {"status": "ok", "result": result}


# ============================================================================
# IRL SAFE MODE — Passive Continuous Transcription
# ============================================================================

class IRLStartRequest(BaseModel):
    safe_scene: str = "BRB"
    danger_phrases: list[str] | None = None


@router.post("/irl/start")
def start_irl_mode(payload: IRLStartRequest, request: Request, db: Session = Depends(get_db)):
    """
    Start IRL Safe Mode. Activates continuous passive audio transcription
    that checks for danger phrases and auto-switches scene on match.
    """
    streamer = _require_streamer(request, db)
    
    from backend.core.irl_transcriber import start_irl_mode
    from backend.commands.executor import CommandExecutor
    
    # Set up callback for danger phrase detection (auto scene switch)
    obs_adapter = getattr(request.app.state, "obs_bridge", None)
    
    async def on_danger_phrase_callback(safe_scene: str):
        """Callback triggered when danger phrase detected."""
        if obs_adapter:
            try:
                result = await obs_adapter.execute("switch_scene", {"scene": safe_scene})
                logger.info(f"IRL: Auto-switched to '{safe_scene}' for streamer {streamer.id}")
                return result
            except Exception as e:
                logger.error(f"IRL: Failed to auto-switch scene: {e}")
    
    async def on_transcription_callback(transcript: str):
        """Optional callback for logging transcriptions."""
        logger.debug(f"IRL: Transcribed ({streamer.id}): {transcript[:100]}")
    
    # Get danger phrases from request or database settings
    danger_phrases = payload.danger_phrases or []
    if not danger_phrases:
        settings = streamer.settings_json or {}
        default_phrases = [
            "my address is", "i live in", "my phone number",
            "don't show this", "wait don't", "actually stop",
            "my full name", "passport", "driver's license",
        ]
        custom = settings.get("irl_custom_phrases", [])
        danger_phrases = default_phrases + custom
    
    result = start_irl_mode(
        streamer_id=streamer.id,
        safe_scene=payload.safe_scene,
        danger_phrases=danger_phrases,
        on_danger_phrase=on_danger_phrase_callback,
        on_transcription=on_transcription_callback,
    )
    
    # Persist settings
    if not streamer.settings_json:
        streamer.settings_json = {}
    streamer.settings_json["irl_mode_active"] = True
    streamer.settings_json["irl_safe_scene"] = payload.safe_scene
    streamer.settings_json["irl_custom_phrases"] = [p for p in danger_phrases if p not in ["my address is", "i live in", "my phone number", "don't show this", "wait don't", "actually stop", "my full name", "passport", "driver's license"]]
    db.add(streamer)
    db.commit()
    
    logger.info(f"IRL mode started for streamer {streamer.id}: safe_scene={payload.safe_scene}")
    return {"status": "ok", "result": result}


@router.post("/irl/stop")
def stop_irl_mode(request: Request, db: Session = Depends(get_db)):
    """Stop IRL Safe Mode and disable passive transcription."""
    streamer = _require_streamer(request, db)
    
    from backend.core.irl_transcriber import stop_irl_mode
    
    result = stop_irl_mode(streamer.id)
    
    # Persist settings
    if not streamer.settings_json:
        streamer.settings_json = {}
    streamer.settings_json["irl_mode_active"] = False
    db.add(streamer)
    db.commit()
    
    logger.info(f"IRL mode stopped for streamer {streamer.id}")
    return {"status": "ok", "result": result}


@router.post("/fingerprint/record", response_model=None)
async def record_voice_fingerprint(
    request: Request,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="Streamer not found")

    # Save the audio file temporarily
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from backend.core.voice_fingerprint import create_voice_fingerprint

        embedding = create_voice_fingerprint(tmp_path)

        if not embedding:
            raise HTTPException(status_code=422, detail="Could not process audio")

        # Save embedding to database
        from backend.database.models.streamer_voice_embedding import StreamerVoiceEmbedding
        import json

        existing = db.query(StreamerVoiceEmbedding).filter(
            StreamerVoiceEmbedding.streamer_id == streamer_id
        ).first()

        if existing:
            existing.embedding = json.dumps(embedding)
        else:
            record = StreamerVoiceEmbedding(
                streamer_id=streamer_id,
                embedding=json.dumps(embedding),
            )
            db.add(record)

        db.commit()
        return {"status": "ok", "message": "Voice fingerprint saved"}
    finally:
        os.unlink(tmp_path)


@router.get("/irl/status")
def get_irl_status(request: Request, db: Session = Depends(get_db)):
    """Get current IRL Safe Mode status."""
    streamer = _require_streamer(request, db)

    from backend.core.irl_transcriber import get_irl_status

    status = get_irl_status(streamer.id)
    return {"status": "ok", "irl": status}

