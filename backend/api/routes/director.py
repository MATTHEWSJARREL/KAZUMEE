from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.core.event_store import insert_stream_event
from backend.core.search import search_links
from backend.core.streamer_ai_suite import PROHIBITED_LABELS, streamer_ai_suite
from backend.core.export import queue_short_form_export
from backend.database.models.clip import Clip
from backend.database.models.command import Command
from backend.database.models.stream_event import StreamEvent
from backend.database.models.streamer import Streamer
from backend.database.models.viewer_action import ViewerAction
from backend.database.session import get_db
from backend.api.dependencies import require_feature
from backend.core.rate_limiter import limiter

router = APIRouter()


class PollRequest(BaseModel):
    topic: str = "next move"
    option_count: int = Field(default=4, ge=2, le=5)


class UniversalSearchRequest(BaseModel):
    query: str
    platforms: list[str] | None = None
    limit: int = Field(default=5, ge=1, le=10)


class BackseatRequest(BaseModel):
    game: str
    context: str = ""
    champion: str | None = None
    links_limit: int = Field(default=2, ge=0, le=5)


class SafetyTriggerRequest(BaseModel):
    risk_score: float = 0.0
    labels: list[str] = []
    safe_scene: str = "BRB"


class VisionScanRequest(BaseModel):
    risk_score: float = 0.0
    labels: list[str] = []
    safe_scene: str = "BRB"
    frame_ref: str | None = None


class AudioLevelRequest(BaseModel):
    source: str = "Mic/Aux"
    db: float = Field(default=-8.0, ge=-60.0, le=20.0)


class ClipNowRequest(BaseModel):
    create_twitch_clip: bool = True
    queue_vertical_export: bool = True
    preset: str = "tiktok"
    title: str | None = None


class AutoPackageRequest(BaseModel):
    preset: str = "tiktok"
    limit: int = Field(default=5, ge=1, le=30)


class ShieldActivateRequest(BaseModel):
    follower_only_minutes: int = Field(default=10, ge=0, le=43200)
    slow_mode_seconds: int = Field(default=5, ge=3, le=120)
    block_links: bool = True


class ModerationEnforceRequest(BaseModel):
    action: str = "timeout"  # timeout | ban
    username: str
    user_id: str | None = None
    duration_seconds: int = Field(default=600, ge=1, le=1209600)
    reason: str = "Kazumi moderation action"


VALID_PLATFORMS = {
    "twitch": "site:twitch.tv",
    "youtube": "site:youtube.com",
    "kick": "site:kick.com",
    "tiktok": "site:tiktok.com",
}


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


@router.post("/api/streamer/director/poll")
def generate_dynamic_poll(payload: PollRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    since = datetime.now(timezone.utc) - timedelta(minutes=30)
    rows = (
        db.query(StreamEvent)
        .filter(
            StreamEvent.streamer_id == streamer.id,
            StreamEvent.created_at >= since,
            StreamEvent.message.isnot(None),
        )
        .order_by(StreamEvent.created_at.desc())
        .limit(300)
        .all()
    )
    messages = [row.message or "" for row in rows]
    poll = streamer_ai_suite.build_dynamic_poll(
        topic=payload.topic,
        recent_messages=messages,
        option_count=payload.option_count,
    )
    return {"status": "success", "poll": poll}


@router.post("/api/streamer/director/search")
async def universal_search(payload: UniversalSearchRequest, request: Request, db: Session = Depends(get_db)):
    _require_streamer(request, db)
    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query required")

    platforms = [p.lower().strip() for p in (payload.platforms or []) if p]
    site_filters = [VALID_PLATFORMS[p] for p in platforms if p in VALID_PLATFORMS]
    full_query = query
    if site_filters:
        full_query = f"{query} ({' OR '.join(site_filters)})"

    results = await search_links(full_query, limit=payload.limit)
    return {
        "status": "success" if results else "no_results",
        "query": full_query,
        "results": results,
    }


@router.post("/api/streamer/director/backseat")
@limiter.limit("30/minute")
async def backseat_advice(
    payload: BackseatRequest,
    request: Request,
    db: Session = Depends(get_db),
    streamer: Streamer = Depends(require_feature("backseat_gaming")),
):
    advice = streamer_ai_suite.build_backseating_advice(
        game=payload.game,
        context=payload.context,
        champion=payload.champion,
    )

    links = []
    if payload.links_limit > 0:
        search_query = f"{payload.game} {payload.context} strategy tips"
        links = await search_links(search_query, limit=payload.links_limit)

    return {
        "status": "success",
        "advice": advice,
        "links": links,
    }


@router.post("/api/streamer/director/safety-trigger")
async def safety_trigger(payload: SafetyTriggerRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    labels = [str(x).strip().lower() for x in payload.labels if str(x).strip()]
    flagged_labels = [label for label in labels if label in PROHIBITED_LABELS]
    risk_score = max(0.0, min(1.0, float(payload.risk_score)))

    threshold = 0.82
    should_trigger = risk_score >= threshold or bool(flagged_labels)

    if should_trigger:
        executor = getattr(request.app.state, "executor", None)
        if executor:
            await executor.execute("panic_mode", {"panic_scene": payload.safe_scene or "BRB"})

        insert_stream_event(
            db,
            streamer_id=streamer.id,
            platform="kazumi_ai",
            event_type="tos_bodyguard_triggered",
            username="Kazumi",
            message="Safety mode triggered by visual risk.",
            payload={
                "risk_score": risk_score,
                "labels": labels,
                "flagged_labels": flagged_labels,
                "safe_scene": payload.safe_scene or "BRB",
            },
        )
        db.commit()

    return {
        "status": "success",
        "triggered": should_trigger,
        "risk_score": risk_score,
        "flagged_labels": flagged_labels,
    }


@router.post("/api/streamer/director/hardware/audio-level")
async def set_hardware_audio_level(payload: AudioLevelRequest, request: Request, db: Session = Depends(get_db)):
    _require_streamer(request, db)
    executor = getattr(request.app.state, "executor", None)
    if not executor:
        raise HTTPException(status_code=503, detail="Executor unavailable")
    result = await executor.execute(
        "set_audio_level",
        {"source": payload.source, "db": payload.db},
    )
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message)
    return {"status": "success", "result": result.data or {"source": payload.source, "db": payload.db}}


@router.get("/api/streamer/director/post-stream-report")
def post_stream_report(request: Request, hours: int = 6, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    lookback = max(1, min(hours, 72))
    since = datetime.now(timezone.utc) - timedelta(hours=lookback)

    event_rows = (
        db.query(StreamEvent)
        .filter(StreamEvent.streamer_id == streamer.id, StreamEvent.created_at >= since)
        .order_by(StreamEvent.created_at.asc())
        .all()
    )
    clip_rows = (
        db.query(Clip)
        .filter(Clip.streamer_id == streamer.id, Clip.created_at >= since)
        .order_by(Clip.created_at.asc())
        .all()
    )
    command_rows = (
        db.query(Command)
        .filter(Command.streamer_id == streamer.id, Command.created_at >= since)
        .order_by(Command.created_at.asc())
        .all()
    )
    viewer_action_rows = (
        db.query(ViewerAction)
        .filter(ViewerAction.streamer_id == streamer.id, ViewerAction.created_at >= since)
        .order_by(ViewerAction.created_at.asc())
        .all()
    )

    report = streamer_ai_suite.build_post_stream_report(
        events=[
            {
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "event_type": row.event_type,
                "message": row.message,
            }
            for row in event_rows
        ],
        clips=[
            {
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "status": row.status,
            }
            for row in clip_rows
        ],
        commands=[
            {
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "status": row.status,
                "intent": row.intent,
            }
            for row in command_rows
        ],
        viewer_actions=[
            {
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "action_type": row.action_type,
                "status": row.status,
                "cost": row.cost,
            }
            for row in viewer_action_rows
        ],
    )

    return {
        "status": "success",
        "window_hours": lookback,
        "streamer_id": streamer.id,
        "report": report,
    }


@router.post("/api/streamer/director/vision-scan")
async def ingest_vision_scan(payload: VisionScanRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    labels = [str(x).strip().lower() for x in payload.labels if str(x).strip()]
    risk_score = max(0.0, min(1.0, float(payload.risk_score)))

    signals = streamer_ai_suite.process_event(
        streamer_id=streamer.id,
        settings_json=streamer.settings_json or {},
        platform="vision",
        event_type="vision_tos_scan",
        username="vision_engine",
        message=None,
        payload={
            "tos_risk_score": risk_score,
            "labels": labels,
            "frame_ref": payload.frame_ref,
            "safe_scene": payload.safe_scene,
        },
        moment_score=None,
    )

    executed_actions = []
    executor = getattr(request.app.state, "executor", None)
    for signal in signals:
        insert_stream_event(
            db,
            streamer_id=streamer.id,
            platform="kazumi_ai",
            event_type=signal.get("event_type", "vision_signal"),
            username="Kazumi",
            message=signal.get("message"),
            payload={"feature": signal.get("feature"), "data": signal.get("data") or {}},
        )
        if signal.get("auto_execute") and executor:
            intent = signal.get("command_intent") or signal.get("event_type")
            command_payload = dict(signal.get("command_payload") or {})
            command_payload.setdefault("streamer_id", streamer.id)
            result = await executor.execute(intent, command_payload)
            executed_actions.append(
                {
                    "intent": intent,
                    "status": result.status,
                    "message": result.message,
                }
            )
    db.commit()

    return {
        "status": "success",
        "signals": signals,
        "executed_actions": executed_actions,
    }


@router.post("/api/streamer/director/clip-now")
async def clip_now(payload: ClipNowRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    executor = getattr(request.app.state, "executor", None)
    if not executor:
        raise HTTPException(status_code=503, detail="Executor unavailable")

    twitch_result = None
    if payload.create_twitch_clip:
        twitch_exec = await executor.execute(
            "create_twitch_clip",
            {"streamer_id": streamer.id, "has_delay": True},
        )
        twitch_result = twitch_exec.data if twitch_exec.data else {"status": twitch_exec.status}

    result = await executor.execute(
        "save_replay_buffer",
        {
            "requester_type": "streamer",
            "requester_name": streamer.display_name or streamer.username,
            "requester_id": streamer.id,
            "auto_export": bool(payload.queue_vertical_export),
            "watermark_text": streamer.display_name or streamer.username,
        },
    )
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message)

    clip_id = (result.data or {}).get("clip_id")
    if not clip_id:
        return {"status": "success", "message": "Clip trigger sent", "clip_id": None}

    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if clip and payload.title:
        clip.title = payload.title
        db.commit()

    return {
        "status": "success",
        "clip_id": clip_id,
        "export_queued": bool(payload.queue_vertical_export),
        "twitch_clip": twitch_result,
    }


@router.post("/api/streamer/director/editor/auto-package")
def auto_package_exports(payload: AutoPackageRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    preset = (payload.preset or "tiktok").strip().lower()
    if preset not in {"tiktok", "shorts", "reels"}:
        raise HTTPException(status_code=400, detail="Invalid preset")

    clips = (
        db.query(Clip)
        .filter(
            Clip.streamer_id == streamer.id,
            Clip.status == "approved",
        )
        .order_by(Clip.created_at.desc())
        .limit(payload.limit)
        .all()
    )

    jobs = []
    for clip in clips:
        if clip.export_status in {"queued", "sent", "executed"}:
            continue
        job = queue_short_form_export(
            db,
            clip_id=clip.id,
            streamer_id=streamer.id,
            input_path=clip.file_path,
            preset=preset,
            watermark_text=streamer.display_name or streamer.username,
            subtitles_path=None,
        )
        clip.export_status = "queued"
        clip.export_preset = preset
        clip.export_path = job.get("output_path")
        clip.export_updated_at = datetime.utcnow()
        jobs.append(job)

    db.commit()
    return {
        "status": "success",
        "queued_jobs": jobs,
        "queued_count": len(jobs),
    }


@router.post("/api/streamer/director/shield/activate")
async def activate_chat_shield(payload: ShieldActivateRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    executor = getattr(request.app.state, "executor", None)
    if not executor:
        raise HTTPException(status_code=503, detail="Executor unavailable")
    result = await executor.execute(
        "lock_chat_follower_only",
        {
            "streamer_id": streamer.id,
            "follower_only_minutes": payload.follower_only_minutes,
            "slow_mode_seconds": payload.slow_mode_seconds,
            "block_links": payload.block_links,
        },
    )
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message)
    return {"status": "success", "result": result.data}


@router.post("/api/streamer/director/moderation/enforce")
async def enforce_moderation(payload: ModerationEnforceRequest, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    action = (payload.action or "").strip().lower()
    if action not in {"timeout", "ban"}:
        raise HTTPException(status_code=400, detail="action must be timeout or ban")
    executor = getattr(request.app.state, "executor", None)
    if not executor:
        raise HTTPException(status_code=503, detail="Executor unavailable")
    result = await executor.execute(
        "moderation_auto_action",
        {
            "streamer_id": streamer.id,
            "action": action,
            "username": payload.username,
            "user_id": payload.user_id,
            "duration_seconds": payload.duration_seconds,
            "reason": payload.reason,
        },
    )
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message)
    return {"status": "success", "result": result.data}
