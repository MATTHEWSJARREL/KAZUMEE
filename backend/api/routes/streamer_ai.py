from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.core.streamer_ai_suite import streamer_ai_suite
from backend.database.models.stream_event import StreamEvent
from backend.database.models.streamer import Streamer
from backend.database.session import get_db


router = APIRouter()


class SeoSuggestionRequest(BaseModel):
    game: str


class ContentFarmAnalyzeRequest(BaseModel):
    clip_id: int | None = None
    transcript: str = ""
    message_velocity: float = 0.0
    laughter_markers: int = 0
    intensity: float = 0.0
    pacing: float = 0.5


class StreamerMessageScanRequest(BaseModel):
    platform: str = "twitch"
    event_type: str = "chat_message"
    username: str = "viewer"
    message: str = ""
    payload: dict | None = None


def _require_streamer(request: Request, db: Session):
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


@router.get("/api/streamer/ai/status")
def streamer_ai_status(request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    status = streamer_ai_suite.summarize_status(streamer.id, streamer.settings_json or {})
    return {"status": "success", **status}


@router.post("/api/streamer/ai/seo-suggestions")
def streamer_ai_seo(payload: SeoSuggestionRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    since = datetime.now(timezone.utc) - timedelta(hours=3)
    rows = (
        db.query(StreamEvent)
        .filter(
            StreamEvent.streamer_id == streamer.id,
            StreamEvent.created_at >= since,
            StreamEvent.message.isnot(None),
        )
        .order_by(StreamEvent.created_at.desc())
        .limit(250)
        .all()
    )
    messages = [row.message or "" for row in rows]
    result = streamer_ai_suite.build_seo_suggestions(
        game=payload.game,
        messages=messages,
        streamer_name=streamer.display_name or streamer.username,
    )
    return {"status": "success", "suggestions": result}


@router.post("/api/streamer/ai/content-farm/analyze")
def streamer_ai_content_farm(payload: ContentFarmAnalyzeRequest, request: Request, db: Session = Depends(get_db)):
    _require_streamer(request, db)
    result = streamer_ai_suite.analyze_content_farm_clip(
        transcript=payload.transcript or "",
        message_velocity=max(0.0, float(payload.message_velocity or 0.0)),
        laughter_markers=max(0, int(payload.laughter_markers or 0)),
        intensity=max(0.0, float(payload.intensity or 0.0)),
        pacing=max(0.0, min(1.0, float(payload.pacing or 0.5))),
    )
    return {"status": "success", "analysis": result}


@router.post("/api/streamer/ai/message-scan")
def streamer_ai_message_scan(payload: StreamerMessageScanRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    signals = streamer_ai_suite.process_event(
        streamer_id=streamer.id,
        settings_json=streamer.settings_json or {},
        platform=payload.platform,
        event_type=payload.event_type,
        username=payload.username,
        message=payload.message,
        payload=payload.payload or {},
        moment_score=None,
    )
    return {"status": "success", "signals": signals}

