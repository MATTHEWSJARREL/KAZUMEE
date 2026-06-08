from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
from pydantic import BaseModel
from backend.api.websockets import manager
from backend.core.auth import (
    get_current_user,
    get_user_from_token,
    get_user_by_id,
    verify_stream_access_token,
    get_streamer_id_for_user,
    resolve_streamer_id,
)
from backend.database.session import SessionLocal
from backend.database.models.stream_event import StreamEvent
from backend.core.event_store import insert_stream_event
from backend.services.scoring import get_meter, can_trigger, rules_from_profile
from backend.database.models.streamer import Streamer
from backend.database.models.command import Command
from backend.database.models.stream_session import StreamSession
from starlette.responses import StreamingResponse
from backend.core.streamer_ai_suite import streamer_ai_suite
import json
import asyncio
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import os
from backend.core.rate_limiter import limiter

router = APIRouter()
ANSWERED_QUESTION_KEYS: dict[int, set[str]] = {}
ALLOW_LEGACY_QUERY_SESSION_TOKEN = os.getenv("ALLOW_LEGACY_QUERY_SESSION_TOKEN", "false").lower() == "true"


def _normalize_message(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s]", "", value)
    return value.strip()


def _sorter_config(streamer: Streamer | None) -> dict:
    defaults = {
        "enabled": True,
        "extractQuestions": True,
        "blockedQuestionKeywords": [],
        "questionSourceMode": "all",  # all | subs_mods
        "muteQuestionsUntil": None,
    }
    settings = (streamer.settings_json or {}) if streamer else {}
    cfg = settings.get("superChatSorter") or {}
    blocked = cfg.get("blockedQuestionKeywords") or []
    if not isinstance(blocked, list):
        blocked = []
    return {
        "enabled": bool(cfg.get("enabled", defaults["enabled"])),
        "extractQuestions": bool(cfg.get("extractQuestions", defaults["extractQuestions"])),
        "blockedQuestionKeywords": [str(x).strip().lower() for x in blocked if str(x).strip()],
        "questionSourceMode": cfg.get("questionSourceMode", "all") if cfg.get("questionSourceMode", "all") in {"all", "subs_mods"} else "all",
        "muteQuestionsUntil": cfg.get("muteQuestionsUntil"),
    }


def _payload_is_sub_or_mod(payload: dict | None) -> bool:
    p = payload or {}
    if p.get("is_subscriber") is True or p.get("subscriber") is True:
        return True
    if p.get("is_moderator") is True or p.get("moderator") is True:
        return True
    badges = p.get("badges")
    if isinstance(badges, list):
        normalized = {str(b).lower() for b in badges}
        if "subscriber" in normalized or "moderator" in normalized or "mod" in normalized:
            return True
    return False


def _is_question_muted(cfg: dict) -> bool:
    raw = cfg.get("muteQuestionsUntil")
    if not raw:
        return False


def _resolve_stream_token_context(token: str) -> tuple[object | None, int | None]:
    claims = verify_stream_access_token(token)
    if claims:
        user = get_user_by_id(int(claims["uid"]))
        streamer_id = int(claims["sid"])
        return user, streamer_id
    if ALLOW_LEGACY_QUERY_SESSION_TOKEN:
        user = get_user_from_token(token)
        if user:
            return user, get_streamer_id_for_user(user)
    return None, None
    try:
        until = datetime.fromisoformat(str(raw))
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < until
    except Exception:
        return False


@router.websocket("/ws/events")
async def events_ws(websocket: WebSocket):
    token = (websocket.query_params.get("token") or "").strip()
    user = None
    streamer_id = None
    if token:
        user, streamer_id = _resolve_stream_token_context(token)
    if not user or not streamer_id:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, streamer_id=streamer_id)
    try:
        while True:
            # keep the connection open; optionally receive pings from client
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                # ignore unexpected receive errors and continue
                continue
    finally:
        manager.disconnect(websocket)


class IngestEventRequest(BaseModel):
    platform: str
    event_type: str
    event_id: str | None = None
    user_id: str | None = None
    username: str | None = None
    message: str | None = None
    payload: dict | None = None


class AnswerQuestionRequest(BaseModel):
    question_key: str


@router.post("/api/ingest")
@limiter.limit("120/minute")
async def ingest_event(request: Request, payload: IngestEventRequest):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    score_payload = None
    streamer_settings = {}
    if payload.message:
        db = SessionLocal()
        try:
            streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
            rules = rules_from_profile(streamer.taste_profile if streamer else None)
            streamer_settings = streamer.settings_json if streamer else {}
        finally:
            db.close()
        meter = get_meter(streamer_id, rules)
        meter.add_message(payload.message)
        intensity = None
        if payload.payload:
            intensity = payload.payload.get("intensity")
        score_payload = meter.score(intensity=intensity)
        if score_payload["confidence"] in {"high", "medium"}:
            await manager.broadcast(
                {
                    "type": "moment_score",
                    "score": score_payload["score"],
                    "confidence": score_payload["confidence"],
                    "signals": score_payload["signals"],
                    "message": payload.message,
                    "streamer_id": streamer_id,
                }
            )

        # Auto-clip policy
        if score_payload["confidence"] == "high" and can_trigger(streamer_id):
            executor = request.app.state.executor
            await executor.execute(
                "save_replay_buffer",
                {
                    "requester_type": "ai_observer",
                    "requester_name": "Kazumi",
                    "requester_id": None,
                    "auto_export": True,
                    "watermark_text": payload.username or "Kazumi",
                },
            )
        elif score_payload["confidence"] == "medium" and can_trigger(streamer_id):
            db = SessionLocal()
            try:
                suggestion = Command(
                    stream_session_id=1,
                    streamer_id=streamer_id,
                    issued_by_type="ai_observer",
                    issued_by_id=None,
                    command_text="AI Suggestion: auto_clip",
                    intent="auto_clip",
                    ai_reasoning="Medium confidence moment detected. Review before clipping.",
                    status="pending",
                    priority_level=50,
                )
                db.add(suggestion)
                db.commit()
            finally:
                db.close()

    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        if streamer and not streamer_settings:
            streamer_settings = streamer.settings_json or {}

        event_id = payload.event_id
        if not event_id and payload.payload:
            event_id = payload.payload.get("id") or payload.payload.get("event_id")
        created = insert_stream_event(
            db,
            streamer_id=streamer_id,
            platform=payload.platform,
            event_type=payload.event_type,
            event_id=event_id,
            user_id=payload.user_id,
            username=payload.username,
            message=payload.message,
            payload=payload.payload,
        )

        suite_signals = streamer_ai_suite.process_event(
            streamer_id=streamer_id,
            settings_json=streamer_settings or {},
            platform=payload.platform,
            event_type=payload.event_type,
            username=payload.username,
            message=payload.message,
            payload=payload.payload or {},
            moment_score=score_payload,
        )

        active_session = (
            db.query(StreamSession)
            .filter(StreamSession.streamer_id == streamer_id, StreamSession.status == "live")
            .order_by(StreamSession.start_time.desc())
            .first()
        )
        if not active_session:
            active_session = StreamSession(streamer_id=streamer_id, status="live")
            db.add(active_session)
            db.flush()

        for idx, signal in enumerate(suite_signals):
            signal_data = signal.get("data") or {}
            insert_stream_event(
                db,
                streamer_id=streamer_id,
                platform="kazumi_ai",
                event_type=signal.get("event_type", "streamer_ai_signal"),
                event_id=f"{event_id or payload.event_type}-{idx}-{int(datetime.now(timezone.utc).timestamp())}",
                username="Kazumi",
                message=signal.get("message"),
                payload={
                    "feature": signal.get("feature"),
                    "severity": signal.get("severity"),
                    "title": signal.get("title"),
                    "data": signal_data,
                    "source_event_type": payload.event_type,
                },
            )

            created_command = None
            if signal.get("create_command"):
                created_command = Command(
                    stream_session_id=active_session.id,
                    streamer_id=streamer_id,
                    issued_by_type="ai_observer",
                    issued_by_id=None,
                    command_text=f"AI Suggestion: {signal.get('title', 'Action')}",
                    intent=signal.get("command_intent") or signal.get("event_type") or "ai_action",
                    ai_reasoning=signal.get("message") or "AI signal detected.",
                    status="pending",
                    confidence_score=1.0,
                    credit_cost=0,
                    priority_level=90 if signal.get("severity") == "critical" else 65,
                )
                db.add(created_command)

            if signal.get("auto_obs_mute"):
                obs_adapter = getattr(request.app.state, "obs_adapter", None)
                source_name = (signal_data.get("source")) or "Desktop Audio"
                if obs_adapter:
                    obs_adapter.set_mute(source_name, True)

            if signal.get("auto_execute"):
                executor = getattr(request.app.state, "executor", None)
                if executor:
                    intent = signal.get("command_intent") or signal.get("event_type")
                    command_payload = dict(signal.get("command_payload") or {})
                    command_payload.setdefault("streamer_id", streamer_id)
                    try:
                        result = await executor.execute(intent, command_payload)
                        if created_command:
                            created_command.status = "executed" if result.status == "ok" else "rejected"
                    except Exception:
                        if created_command:
                            created_command.status = "rejected"

        db.commit()
        return {
            "status": "success",
            "created": created,
            "moment_score": score_payload,
            "streamer_ai_signals": suite_signals,
        }
    finally:
        db.close()


@router.get("/api/events/stream")
async def stream_events(request: Request):
    query_token = (request.query_params.get("token") or "").strip()
    user = None
    streamer_id = None
    if query_token:
        user, streamer_id = _resolve_stream_token_context(query_token)
    if not user:
        user = get_current_user(request, required=False)
        streamer_id = resolve_streamer_id(request, user)

    query_streamer = request.query_params.get("streamer_id")
    if query_streamer and user:
        try:
            query_id = int(query_streamer)
        except ValueError:
            query_id = None
        if query_id is not None:
            if user.role == "viewer":
                active_id = get_streamer_id_for_user(user)
                if active_id != query_id:
                    return StreamingResponse(iter(()), media_type="text/event-stream")
                streamer_id = active_id
            elif user.role == "streamer":
                streamer_id = get_streamer_id_for_user(user)
    if not streamer_id:
        return StreamingResponse(iter(()), media_type="text/event-stream")

    async def event_generator():
        last_id = 0
        while True:
            db = SessionLocal()
            try:
                rows = (
                    db.query(StreamEvent)
                    .filter(StreamEvent.streamer_id == streamer_id, StreamEvent.id > last_id)
                    .order_by(StreamEvent.id.asc())
                    .limit(50)
                    .all()
                )
                for row in rows:
                    last_id = row.id
                    payload = {
                        "id": row.id,
                        "platform": row.platform,
                        "event_type": row.event_type,
                        "username": row.username or "",
                        "message": row.message or "",
                        "payload": row.payload or {},
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
            finally:
                db.close()
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/api/events/recent")
async def recent_events(request: Request, limit: int = 50):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    db = SessionLocal()
    try:
        rows = (
            db.query(StreamEvent)
            .filter(StreamEvent.streamer_id == streamer_id)
            .order_by(StreamEvent.id.desc())
            .limit(min(limit, 200))
            .all()
        )
        events = [
            {
                "id": row.id,
                "platform": row.platform,
                "event_type": row.event_type,
                "username": row.username or "",
                "message": row.message or "",
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
        return {"events": list(reversed(events))}
    finally:
        db.close()


@router.get("/api/events/streamer-view")
async def streamer_view(request: Request, window_minutes: int = 10, limit: int = 300):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")

    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=max(1, min(window_minutes, 120)))

    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        sorter_cfg = _sorter_config(streamer)
        if not sorter_cfg["enabled"]:
            return {
                "window_minutes": window_minutes,
                "grouped_notifications": [],
                "to_answer": [],
                "stats": {
                    "messages_scanned": 0,
                    "groups_detected": 0,
                    "questions_detected": 0,
                },
                "config": sorter_cfg,
            }

        rows = (
            db.query(StreamEvent)
            .filter(
                StreamEvent.streamer_id == streamer_id,
                StreamEvent.created_at >= since,
                StreamEvent.message.isnot(None),
            )
            .order_by(StreamEvent.created_at.desc())
            .limit(min(limit, 1000))
            .all()
        )

        grouped = defaultdict(lambda: {"count": 0, "users": set(), "last_seen": None, "message": "", "platform": "", "event_type": ""})
        questions = []
        seen_questions = set()
        answered_keys = ANSWERED_QUESTION_KEYS.get(streamer_id, set())
        questions_muted = _is_question_muted(sorter_cfg)

        for row in rows:
            message = (row.message or "").strip()
            if not message:
                continue

            key = _normalize_message(message)
            if key:
                bucket = grouped[key]
                bucket["count"] += 1
                if row.username:
                    bucket["users"].add(row.username)
                bucket["last_seen"] = max(bucket["last_seen"], row.created_at) if bucket["last_seen"] else row.created_at
                if not bucket["message"]:
                    bucket["message"] = message
                    bucket["platform"] = row.platform
                    bucket["event_type"] = row.event_type

            if sorter_cfg["extractQuestions"] and (not questions_muted) and "?" in message:
                lowered = message.lower()
                if any(keyword in lowered for keyword in sorter_cfg["blockedQuestionKeywords"]):
                    continue
                if sorter_cfg["questionSourceMode"] == "subs_mods" and not _payload_is_sub_or_mod(row.payload):
                    continue
                qkey = _normalize_message(message)
                if qkey and qkey not in seen_questions and qkey not in answered_keys:
                    seen_questions.add(qkey)
                    questions.append(
                        {
                            "id": row.id,
                            "question_key": qkey,
                            "username": row.username or "Anonymous",
                            "message": message,
                            "platform": row.platform,
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                            "is_sub_or_mod": _payload_is_sub_or_mod(row.payload),
                        }
                    )

        grouped_notifications = []
        for value in grouped.values():
            if value["count"] < 2:
                continue
            grouped_notifications.append(
                {
                    "message": value["message"],
                    "count": value["count"],
                    "platform": value["platform"],
                    "event_type": value["event_type"],
                    "sample_users": sorted(list(value["users"]))[:5],
                    "last_seen": value["last_seen"].isoformat() if value["last_seen"] else None,
                }
            )

        grouped_notifications.sort(key=lambda x: x["count"], reverse=True)

        return {
            "window_minutes": window_minutes,
            "grouped_notifications": grouped_notifications[:12],
            "to_answer": questions[:20],
            "config": sorter_cfg,
            "stats": {
                "messages_scanned": len(rows),
                "groups_detected": len(grouped_notifications),
                "questions_detected": len(questions),
            },
        }
    finally:
        db.close()


@router.post("/api/events/streamer-view/answer")
async def mark_question_answered(request: Request, payload: AnswerQuestionRequest):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    key = (payload.question_key or "").strip().lower()
    if not key:
        raise HTTPException(status_code=400, detail="question_key required")

    bucket = ANSWERED_QUESTION_KEYS.setdefault(streamer_id, set())
    bucket.add(key)
    if len(bucket) > 2000:
        # Keep memory bounded for long-running demo sessions.
        trimmed = list(bucket)[-1500:]
        ANSWERED_QUESTION_KEYS[streamer_id] = set(trimmed)
    return {"status": "success", "question_key": key}

