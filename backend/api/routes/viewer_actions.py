import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.database.models.viewer import Viewer
from backend.database.models.clip import Clip
from backend.database.models.streamer import Streamer
from backend.database.models.stream_session import StreamSession
from backend.database.models.viewer_action import ViewerAction
from backend.database.models.stream_event import StreamEvent
from backend.database.models.platform_connection import PlatformConnection
from sqlalchemy import or_, text
from backend.core.auth import get_current_user, resolve_streamer_id
from backend.core.vote_engine import get_vote_window
from backend.core.event_store import insert_stream_event
from backend.core.export import queue_short_form_export
from backend.core.pricing import limit_violation
from backend.core.crypto import decrypt_token
from backend.core.rate_limiter import limiter

router = APIRouter()


class VoteRequest(BaseModel):
    scene: str


class RedeemRequest(BaseModel):
    action: str  # export_clip
    clip_id: int
    preset: str = "tiktok"


class SoundRequest(BaseModel):
    sound: str


class CompanionAnalyzeRequest(BaseModel):
    message: str


class CompanionSentRequest(BaseModel):
    original_message: str
    sent_message: str | None = None


class CompanionAnswerRequest(BaseModel):
    tracking_id: int


class CompanionRetryRequest(BaseModel):
    tracking_id: int


class CatchupHighlightRequest(BaseModel):
    limit: int = 3


class ChatCleansePreferencesRequest(BaseModel):
    enabled: bool = True
    mode: str = "balanced"  # chill | balanced | strict | custom
    local_scoring_only: bool = True
    hide_aggression: bool = True
    hide_spam: bool = True
    hide_caps: bool = True
    aggression_threshold: float = 2.0
    spam_threshold: int = 5
    caps_threshold_pct: int = 90
    whitelist: list[str] = []


class ChatCleanseScoreRequest(BaseModel):
    message: str
    mode: str = "balanced"
    repeated_count_30s: int = 1
    whitelist: list[str] = []


class ViewerPreferencesRequest(BaseModel):
    theme: str = "system"  # system | light | dark
    layout_mode: str = "focus"  # focus | full
    compact_mode: bool = False
    show_hidden_default: bool = False
    latency_ms: int = 3500


class ViewerClipRequest(BaseModel):
    command: str
    note: str | None = None


class VibeMatcherRecommendation(BaseModel):
    streamer_id: int
    display_name: str
    username: str
    platform: str
    mood_match_score: int
    chat_per_min: float
    hype_signals: int
    audio_energy_estimate: float
    reason: str


CHAT_CLEANSE_MODE_THRESHOLDS = {
    "chill": {"aggression_threshold": 3.0, "spam_threshold": 8, "caps_threshold_pct": 100},
    "balanced": {"aggression_threshold": 2.0, "spam_threshold": 5, "caps_threshold_pct": 90},
    "strict": {"aggression_threshold": 1.0, "spam_threshold": 3, "caps_threshold_pct": 65},
}


def _default_chat_cleanse_preferences() -> dict:
    return {
        "enabled": True,
        "mode": "balanced",
        "local_scoring_only": True,
        "hide_aggression": True,
        "hide_spam": True,
        "hide_caps": True,
        "aggression_threshold": 2.0,
        "spam_threshold": 5,
        "caps_threshold_pct": 90,
        "whitelist": [],
    }


def _default_viewer_preferences() -> dict:
    return {
        "theme": "system",
        "layout_mode": "focus",
        "compact_mode": False,
        "show_hidden_default": False,
        "latency_ms": 3500,
    }


def _ensure_viewer_preferences_column(db: Session):
    # Safe runtime fallback for environments where migrations are not applied yet.
    try:
        db.execute(text("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS preferences_json json"))
        db.commit()
        return
    except Exception:
        db.rollback()
    try:
        db.execute(text("ALTER TABLE viewers ADD COLUMN preferences_json json"))
        db.commit()
    except Exception:
        db.rollback()


def _normalize_whitelist(items: list[str] | None) -> list[str]:
    values = []
    for item in (items or []):
        text_value = (item or "").strip()
        if not text_value:
            continue
        values.append(text_value[:40].lower())
    return values[:80]


def _normalize_viewer_preferences(payload: dict | None) -> dict:
    base = _default_viewer_preferences()
    source = payload or {}
    merged = {**base, **source}

    theme = str(merged.get("theme", base["theme"])).strip().lower()
    if theme not in {"system", "light", "dark"}:
        theme = base["theme"]

    layout_mode = str(merged.get("layout_mode", base["layout_mode"])).strip().lower()
    if layout_mode not in {"focus", "full"}:
        layout_mode = base["layout_mode"]

    try:
        latency_ms = int(merged.get("latency_ms", base["latency_ms"]))
    except Exception:
        latency_ms = base["latency_ms"]
    latency_ms = max(2000, min(8000, latency_ms))

    return {
        "theme": theme,
        "layout_mode": layout_mode,
        "compact_mode": bool(merged.get("compact_mode", base["compact_mode"])),
        "show_hidden_default": bool(merged.get("show_hidden_default", base["show_hidden_default"])),
        "latency_ms": latency_ms,
    }


def _viewer_preferences_bundle(viewer: Viewer) -> dict:
    raw = viewer.preferences_json if isinstance(viewer.preferences_json, dict) else {}
    if "chat_cleanse" in raw or "ui" in raw:
        chat_src = raw.get("chat_cleanse") or {}
        ui_src = raw.get("ui") or {}
    else:
        # Backward compatibility: old payload stored chat-cleanse fields at root.
        chat_src = raw
        ui_src = {}

    return {
        "chat_cleanse": _normalize_chat_cleanse_preferences(chat_src),
        "ui": _normalize_viewer_preferences(ui_src),
    }


def _contains_disallowed_clip_phrase(text_value: str) -> bool:
    lowered = (text_value or "").lower()
    blocked_terms = [
        "nude",
        "nudity",
        "porn",
        "sex",
        "minor",
        "cp",
        "gore",
        "beheading",
        "kill yourself",
        "kys",
        "slur",
    ]
    return any(term in lowered for term in blocked_terms)


def _normalize_chat_cleanse_preferences(payload: dict | None) -> dict:
    base = _default_chat_cleanse_preferences()
    source = payload or {}

    mode = str(source.get("mode", base["mode"])).strip().lower()
    if mode not in {"chill", "balanced", "strict", "custom"}:
        mode = base["mode"]

    merged = {**base, **source}
    merged["mode"] = mode
    merged["enabled"] = bool(source.get("enabled", base["enabled"]))
    merged["local_scoring_only"] = bool(source.get("local_scoring_only", base["local_scoring_only"]))
    merged["hide_aggression"] = bool(source.get("hide_aggression", base["hide_aggression"]))
    merged["hide_spam"] = bool(source.get("hide_spam", base["hide_spam"]))
    merged["hide_caps"] = bool(source.get("hide_caps", base["hide_caps"]))

    try:
        merged["aggression_threshold"] = float(source.get("aggression_threshold", base["aggression_threshold"]))
    except Exception:
        merged["aggression_threshold"] = base["aggression_threshold"]
    merged["aggression_threshold"] = max(0.5, min(3.5, merged["aggression_threshold"]))

    try:
        merged["spam_threshold"] = int(source.get("spam_threshold", base["spam_threshold"]))
    except Exception:
        merged["spam_threshold"] = base["spam_threshold"]
    merged["spam_threshold"] = max(2, min(12, merged["spam_threshold"]))

    try:
        merged["caps_threshold_pct"] = int(source.get("caps_threshold_pct", base["caps_threshold_pct"]))
    except Exception:
        merged["caps_threshold_pct"] = base["caps_threshold_pct"]
    merged["caps_threshold_pct"] = max(40, min(100, merged["caps_threshold_pct"]))
    merged["whitelist"] = _normalize_whitelist(source.get("whitelist"))
    return merged


def _require_viewer(request: Request) -> Viewer:
    user = get_current_user(request, required=True)
    if user.role != "viewer":
        raise HTTPException(status_code=403, detail="Viewer role required")
    return user


def _optional_viewer(request: Request, db: Session) -> tuple[Viewer | None, int | None]:
    try:
        user = get_current_user(request, required=False)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        user = None
    viewer = None
    if user and user.role == "viewer":
        viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()

    streamer_id = resolve_streamer_id(request, user) if user else None
    if not streamer_id:
        raw_streamer_id = (
            request.headers.get("X-Streamer-Id")
            or request.query_params.get("streamer_id")
            or request.query_params.get("s")
        )
        if raw_streamer_id:
            try:
                streamer_id = int(raw_streamer_id)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="invalid streamer_id")

    return viewer, streamer_id


def _enforce_limit(db: Session, viewer: Viewer, action_type: str, limit_key: str, period: str = "day"):
    violation = limit_violation(
        db=db,
        viewer_id=viewer.id,
        viewer_tier=viewer.tier,
        action_type=action_type,
        limit_key=limit_key,
        period=period,
    )
    if violation:
        raise HTTPException(status_code=429, detail=violation["message"])


def _normalize_text(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s?]", "", text)
    return text.strip()


def _all_caps_ratio(value: str) -> float:
    words = re.findall(r"\b[\w']+\b", value or "")
    if not words:
        return 0.0
    caps_count = sum(1 for w in words if len(w) > 2 and w.upper() == w)
    return caps_count / len(words)


def _aggression_score(value: str) -> float:
    text_value = (value or "").lower()
    aggressive_terms = [
        "idiot", "moron", "stupid", "trash", "garbage", "kill", "hate", "loser", "dumb", "pathetic",
        "shut up", "kys",
    ]
    score = 0.0
    for term in aggressive_terms:
        if term in text_value:
            score += 1.0
    if re.search(r"[!?]{3,}", value or ""):
        score += 0.5
    return score


def _is_hype_message(value: str) -> bool:
    text_value = (value or "").lower()
    hype_tokens = [
        "lets go", "let's go", "lfg", "pog", "poggers", "gg", "hype", "wooo", "wooo", "sheesh",
    ]
    return any(token in text_value for token in hype_tokens)


def _score_chat_cleanse_message(message: str, mode: str, repeated_count_30s: int, whitelist: list[str]) -> dict:
    normalized = _normalize_text(message)
    whitelist_set = {w for w in _normalize_whitelist(whitelist)}
    if normalized and normalized in whitelist_set:
        return {"hide": False, "reason": "", "scores": {"aggression": 0, "caps_ratio": 0, "repeated_count_30s": repeated_count_30s}}

    thresholds = CHAT_CLEANSE_MODE_THRESHOLDS.get(mode, CHAT_CLEANSE_MODE_THRESHOLDS["balanced"])
    aggression = _aggression_score(message)
    caps_ratio = _all_caps_ratio(message)
    repeated = max(1, int(repeated_count_30s or 1))
    is_hype = _is_hype_message(message)

    reason = ""
    if aggression >= thresholds["aggression_threshold"]:
        reason = "aggression"
    elif repeated >= thresholds["spam_threshold"]:
        reason = "spam"
    elif caps_ratio >= (thresholds["caps_threshold_pct"] / 100):
        reason = "caps"

    # Context-aware: hype is allowed unless strict mode is hit by repeated spam.
    if is_hype and mode != "strict":
        reason = ""
    elif is_hype and mode == "strict" and reason in {"aggression", "caps"}:
        reason = ""

    return {
        "hide": bool(reason),
        "reason": reason,
        "scores": {
            "aggression": round(aggression, 2),
            "caps_ratio": round(caps_ratio, 2),
            "repeated_count_30s": repeated,
            "is_hype": is_hype,
        },
    }


def _chat_caps_ratio(messages: list[str]) -> float:
    total = 0.0
    count = 0
    for msg in messages:
        if not msg:
            continue
        total += _all_caps_ratio(msg)
        count += 1
    return (total / count) if count else 0.0


def _hype_signal_count(messages: list[str]) -> int:
    tokens = [
        "lets go", "let's go", "lfg", "pog", "poggers", "hype", "gg", "clutch", "insane", "gooo",
    ]
    hits = 0
    for msg in messages:
        lower = (msg or "").lower()
        hits += sum(1 for token in tokens if token in lower)
    return hits


def _audio_energy_estimate(rows: list[StreamEvent]) -> float:
    values = []
    for row in rows:
        payload = row.payload or {}
        for key in ("audio_energy", "rms", "loudness_norm", "energy"):
            raw = payload.get(key)
            if raw is None:
                continue
            try:
                values.append(float(raw))
            except Exception:
                continue
    if not values:
        return 0.0
    avg = sum(values) / max(len(values), 1)
    return max(0.0, min(1.0, avg))


def _vibe_match_score(
    mood: str,
    chat_per_min: float,
    hype_signals: int,
    caps_ratio: float,
    audio_energy: float,
) -> tuple[int, str]:
    # Scale to stable ranges.
    chat_factor = min(1.0, chat_per_min / 20.0)
    hype_factor = min(1.0, hype_signals / 15.0)
    caps_factor = min(1.0, caps_ratio)
    audio_factor = min(1.0, max(0.0, audio_energy))

    if mood == "hype":
        score_f = (
            (chat_factor * 0.35)
            + (hype_factor * 0.35)
            + (caps_factor * 0.10)
            + (audio_factor * 0.20)
        )
        reason = f"Fast chat ({chat_per_min:.1f}/min) with {hype_signals} hype cues."
    else:
        calm_chat = 1.0 - chat_factor
        calm_hype = 1.0 - hype_factor
        calm_caps = 1.0 - caps_factor
        calm_audio = 1.0 - audio_factor
        score_f = (
            (calm_chat * 0.45)
            + (calm_hype * 0.30)
            + (calm_caps * 0.10)
            + (calm_audio * 0.15)
        )
        reason = f"Calmer pace ({chat_per_min:.1f}/min) with lower hype intensity."

    score = int(max(1, min(100, round(score_f * 100))))
    return score, reason


def _keywords(value: str) -> list[str]:
    words = re.findall(r"\b[a-z0-9]{4,}\b", _normalize_text(value))
    stop = {"what", "when", "where", "which", "why", "how", "this", "that", "with", "from", "have", "about"}
    return [w for w in words if w not in stop][:8]


def _improve_question(message: str) -> str:
    text = (message or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[!?]{2,}", "?", text)
    if text and "?" not in text and any(w in text.lower() for w in ["what", "when", "where", "which", "why", "how", "can", "does"]):
        text += "?"
    return text[:240]


def _retry_variant(message: str) -> str:
    text = _normalize_text(message).replace(" ?", "?")
    # Strip filler phrases for a cleaner second attempt.
    text = re.sub(r"\b(please|kinda|maybe|just|really|literally|actually)\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text and "?" not in text:
        text += "?"
    return text[:180]


def _infer_mood(messages: list[str]) -> str:
    neg = {"tilt", "frustrated", "angry", "bad", "stuck", "pain", "annoyed", "rage"}
    pos = {"hype", "clean", "nice", "pog", "good", "clutch", "win", "let's go", "lets go"}
    neg_hits = 0
    pos_hits = 0
    for msg in messages:
        text = (msg or "").lower()
        neg_hits += sum(1 for w in neg if w in text)
        pos_hits += sum(1 for w in pos if w in text)
    if neg_hits > pos_hits + 2:
        return "Frustrated but determined"
    if pos_hits > neg_hits + 2:
        return "Confident and energetic"
    return "Focused and steady"


def _infer_goal(messages: list[str]) -> str:
    hints = [
        "beat", "boss", "rank", "speedrun", "quest", "challenge", "malenia", "raid", "final"
    ]
    for msg in reversed(messages):
        lower = (msg or "").lower()
        if any(h in lower for h in hints):
            return msg[:120]
    return "Progress current objective"


def _top_topics(messages: list[str], limit: int = 3) -> list[str]:
    stop = {
        "what", "when", "where", "which", "why", "how", "this", "that", "with", "from",
        "have", "about", "there", "their", "they", "just", "really", "been", "were", "will",
        "would", "could", "should", "im", "you", "your", "ours", "them", "then", "than"
    }
    words = []
    for msg in messages:
        words.extend([w for w in re.findall(r"\b[a-z0-9]{4,}\b", (msg or "").lower()) if w not in stop])
    counts = Counter(words)
    return [word for word, _ in counts.most_common(limit)]


def _weighted_recent_messages(rows: list[StreamEvent]) -> list[str]:
    now = datetime.now(timezone.utc)
    weighted = []
    for row in rows:
        if not row.message:
            continue
        created = row.created_at or now
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_min = max(0.0, (now - created).total_seconds() / 60.0)
        weight = 3 if age_min <= 20 else (2 if age_min <= 60 else 1)
        weighted.extend([row.message] * weight)
    return weighted


def _companion_status(db: Session, streamer: Streamer, normalized_key: str, created_at: datetime) -> dict:
    since = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    # Use raw model import locally to avoid circular references at import time.
    from backend.database.models.stream_event import StreamEvent

    recent = (
        db.query(StreamEvent)
        .filter(StreamEvent.streamer_id == streamer.id, StreamEvent.created_at >= since)
        .order_by(StreamEvent.created_at.asc())
        .all()
    )

    dup_count = 0
    stream_reply = False
    key_tokens = set(_keywords(normalized_key))
    for row in recent:
        msg = _normalize_text(row.message or "")
        if not msg:
            continue
        if msg == normalized_key:
            dup_count += 1
        if key_tokens and row.username and row.username in {streamer.username, streamer.display_name}:
            msg_tokens = set(_keywords(msg))
            if len(key_tokens.intersection(msg_tokens)) >= max(1, min(3, len(key_tokens) // 2)):
                stream_reply = True

    elapsed_min = (datetime.now(timezone.utc) - since).total_seconds() / 60
    if stream_reply:
        status = "answered"
    elif dup_count >= 6:
        status = "likely_seen"
    elif dup_count >= 3:
        status = "grouped"
    elif elapsed_min >= 3 and dup_count == 0:
        status = "needs_retry"
    else:
        status = "sent"

    return {"status": status, "duplicate_count": dup_count, "elapsed_min": round(elapsed_min, 1)}


@router.get("/api/viewer/credits")
def get_viewer_credits(request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    _ensure_viewer_preferences_column(db)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    return {"credits": viewer.credits, "total_spent": viewer.total_spent}


@router.get("/api/viewer/preferences")
def get_viewer_preferences(request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    _ensure_viewer_preferences_column(db)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    bundle = _viewer_preferences_bundle(viewer)
    if not viewer.preferences_json:
        viewer.preferences_json = bundle
        db.commit()
    return {"status": "success", "preferences": bundle["ui"]}


@router.put("/api/viewer/preferences")
def set_viewer_preferences(
    payload: ViewerPreferencesRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_viewer(request)
    _ensure_viewer_preferences_column(db)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    raw = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    bundle = _viewer_preferences_bundle(viewer)
    bundle["ui"] = _normalize_viewer_preferences(raw)
    viewer.preferences_json = bundle
    db.commit()
    return {"status": "success", "preferences": bundle["ui"]}


@router.get("/api/viewer/chat-cleanse/preferences")
def get_chat_cleanse_preferences(request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    _ensure_viewer_preferences_column(db)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    bundle = _viewer_preferences_bundle(viewer)
    preferences = bundle["chat_cleanse"]
    if not viewer.preferences_json:
        viewer.preferences_json = bundle
        db.commit()
    return {"status": "success", "preferences": preferences}


@router.put("/api/viewer/chat-cleanse/preferences")
def set_chat_cleanse_preferences(
    payload: ChatCleansePreferencesRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_viewer(request)
    _ensure_viewer_preferences_column(db)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    raw = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    normalized = _normalize_chat_cleanse_preferences(raw)
    bundle = _viewer_preferences_bundle(viewer)
    bundle["chat_cleanse"] = normalized
    viewer.preferences_json = bundle
    db.commit()
    return {"status": "success", "preferences": normalized}


@router.post("/api/viewer/chat-cleanse/score")
def score_chat_cleanse_message(payload: ChatCleanseScoreRequest, request: Request, db: Session = Depends(get_db)):
    _ = db
    _require_viewer(request)
    mode = (payload.mode or "balanced").strip().lower()
    if mode not in {"chill", "balanced", "strict", "custom"}:
        mode = "balanced"
    effective_mode = "balanced" if mode == "custom" else mode
    result = _score_chat_cleanse_message(
        message=payload.message or "",
        mode=effective_mode,
        repeated_count_30s=max(1, int(payload.repeated_count_30s or 1)),
        whitelist=payload.whitelist or [],
    )
    return {"status": "success", **result}


@router.post("/api/viewer/clip/request")
async def request_primary_clip(payload: ViewerClipRequest, request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="Select an active streamer first.")

    command_text = (payload.command or "").strip()
    if not command_text:
        raise HTTPException(status_code=400, detail="Command is required.")
    if _contains_disallowed_clip_phrase(command_text):
        raise HTTPException(status_code=403, detail="Clip request denied by safety policy.")

    connection = (
        db.query(PlatformConnection)
        .filter(
            PlatformConnection.streamer_id == streamer_id,
            PlatformConnection.platform == "twitch",
        )
        .first()
    )
    if not connection or not connection.access_token:
        raise HTTPException(
            status_code=409,
            detail="Primary viewer clipping requires Twitch connection for this streamer. Secondary clipping is disabled for viewers.",
        )

    meta = connection.meta or {}
    broadcaster_id = meta.get("broadcaster_id")
    if not broadcaster_id:
        raise HTTPException(
            status_code=409,
            detail="Twitch broadcaster_id is missing. Open Integrations and save Twitch metadata first.",
        )

    client_id = (os.getenv("TWITCH_CLIENT_ID") or "").strip()
    if not client_id:
        raise HTTPException(status_code=500, detail="Server Twitch client ID is not configured.")

    try:
        twitch_token = decrypt_token(connection.access_token)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not read Twitch connection token.")

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                "https://api.twitch.tv/helix/clips",
                params={"broadcaster_id": str(broadcaster_id), "has_delay": "true"},
                headers={
                    "Client-Id": client_id,
                    "Authorization": f"Bearer {twitch_token}",
                },
            )
    except Exception:
        raise HTTPException(status_code=502, detail="Twitch clip request failed.")

    if response.status_code >= 300:
        detail = (response.text or "").strip()
        if response.status_code in {401, 403}:
            raise HTTPException(
                status_code=409,
                detail="Twitch token is invalid or missing clips:edit scope. Reconnect Twitch integration with clip permission.",
            )
        raise HTTPException(status_code=502, detail=detail or "Twitch clip API error.")

    body = response.json() if response.content else {}
    clip_data = (body.get("data") or [{}])[0]
    clip_id = clip_data.get("id")
    edit_url = clip_data.get("edit_url")

    db.add(
        ViewerAction(
            streamer_id=streamer_id,
            viewer_id=viewer.id,
            action_type="request_clip_primary",
            target=str(clip_id or ""),
            cost=0,
            status="executed",
            payload={"source": "twitch_primary", "command": command_text[:200], "edit_url": edit_url},
        )
    )
    insert_stream_event(
        db,
        streamer_id=streamer_id,
        platform="viewer",
        event_type="viewer_clip_requested",
        user_id=str(viewer.id),
        username=viewer.username,
        message="Viewer requested a primary Twitch clip.",
        payload={"clip_id": clip_id, "source": "twitch_primary"},
    )
    if clip_id:
        insert_stream_event(
            db,
            streamer_id=streamer_id,
            platform="twitch",
            event_type="viewer_clip_ready",
            event_id=f"viewer_clip_ready:{clip_id}",
            user_id=str(viewer.id),
            username=viewer.username,
            message=f"Twitch clip ready: {clip_id}",
            payload={
                "clip_id": clip_id,
                "source": "twitch_primary",
                "edit_url": edit_url,
                "moment_label": "Live Twitch clip",
            },
        )
    db.commit()

    return {
        "status": "success",
        "source": "twitch_primary",
        "clip_id": clip_id,
        "edit_url": edit_url,
        "message": "Clip requested on Twitch. Finalization may take a few seconds on Twitch.",
    }


@router.get("/api/viewer/vibe-matcher/recommendations")
def vibe_matcher_recommendations(
    request: Request,
    db: Session = Depends(get_db),
    mood: str = "chill",
    limit: int = 5,
):
    _require_viewer(request)
    mood_value = (mood or "chill").strip().lower()
    if mood_value not in {"chill", "hype"}:
        raise HTTPException(status_code=400, detail="mood must be chill or hype")

    safe_limit = max(1, min(limit, 12))
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=10)

    sessions = (
        db.query(StreamSession)
        .filter(StreamSession.status == "live")
        .order_by(StreamSession.start_time.desc())
        .limit(50)
        .all()
    )
    if not sessions:
        return {"status": "success", "mood": mood_value, "recommendations": []}

    streamer_ids = [s.streamer_id for s in sessions if s.streamer_id]
    streamers = db.query(Streamer).filter(Streamer.id.in_(streamer_ids)).all() if streamer_ids else []
    streamer_map = {s.id: s for s in streamers}

    recommendations: list[VibeMatcherRecommendation] = []
    for session in sessions:
        streamer = streamer_map.get(session.streamer_id)
        if not streamer:
            continue

        rows = (
            db.query(StreamEvent)
            .filter(
                StreamEvent.streamer_id == streamer.id,
                StreamEvent.created_at >= since,
                StreamEvent.message.isnot(None),
            )
            .order_by(StreamEvent.created_at.desc())
            .limit(400)
            .all()
        )
        messages = [r.message or "" for r in rows]
        chat_count = len(messages)
        chat_per_min = round(chat_count / 10.0, 2)
        hype_signals = _hype_signal_count(messages)
        caps_ratio = _chat_caps_ratio(messages)
        audio_energy = _audio_energy_estimate(rows)
        score, reason = _vibe_match_score(
            mood=mood_value,
            chat_per_min=chat_per_min,
            hype_signals=hype_signals,
            caps_ratio=caps_ratio,
            audio_energy=audio_energy,
        )

        recommendations.append(
            VibeMatcherRecommendation(
                streamer_id=streamer.id,
                display_name=streamer.display_name or streamer.username,
                username=streamer.username,
                platform=streamer.platform or "unknown",
                mood_match_score=score,
                chat_per_min=chat_per_min,
                hype_signals=hype_signals,
                audio_energy_estimate=round(audio_energy, 2),
                reason=reason,
            )
        )

    recommendations.sort(key=lambda item: item.mood_match_score, reverse=True)
    return {
        "status": "success",
        "mood": mood_value,
        "recommendations": [item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in recommendations[:safe_limit]],
    }


@router.post("/api/viewer/vote")
def vote_scene(payload: VoteRequest, request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    _enforce_limit(db, viewer, action_type="vote_scene", limit_key="votes_per_day", period="day")

    cost = 1
    if viewer.credits < cost:
        raise HTTPException(status_code=402, detail="Not enough credits")

    viewer.credits -= cost
    viewer.total_spent += cost

    action = ViewerAction(
        streamer_id=streamer_id,
        viewer_id=viewer.id,
        action_type="vote_scene",
        target=payload.scene,
        cost=cost,
        status="queued",
    )
    db.add(action)

    insert_stream_event(
        db,
        streamer_id=streamer_id,
        platform="viewer",
        event_type="vote_scene",
        user_id=str(viewer.id),
        username=viewer.username,
        message=f"Voted for scene: {payload.scene}",
        payload={"scene": payload.scene, "cost": cost},
    )

    counts, winner = get_vote_window(streamer_id).record_vote(payload.scene)

    if winner:
        executor = request.app.state.executor
        if executor:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(executor.execute("switch_scene", {"scene": winner}))
                except RuntimeError:
                    asyncio.run(executor.execute("switch_scene", {"scene": winner}))
            except Exception:
                pass

        insert_stream_event(
            db,
            streamer_id=streamer_id,
            platform="viewer",
            event_type="viewer_impact",
            user_id=str(viewer.id),
            username=viewer.username,
            message=f"Viewer vote switched to {winner}",
            payload={"scene": winner, "counts": counts},
        )
        action.status = "executed"
    else:
        action.status = "queued"

    db.commit()
    return {"status": "success", "counts": counts, "winner": winner, "credits": viewer.credits}


@router.post("/api/viewer/redeem")
def redeem_clip_export(payload: RedeemRequest, request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    if payload.action != "export_clip":
        raise HTTPException(status_code=400, detail="Invalid action")
    _enforce_limit(db, viewer, action_type="export_clip", limit_key="exports_per_month", period="month")

    clip = db.query(Clip).filter(Clip.id == payload.clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    if clip.streamer_id != streamer_id:
        raise HTTPException(status_code=403, detail="Clip is not part of your active streamer")

    cost = 10
    if viewer.credits < cost:
        raise HTTPException(status_code=402, detail="Not enough credits")

    viewer.credits -= cost
    viewer.total_spent += cost

    job = queue_short_form_export(
        db,
        clip_id=clip.id,
        streamer_id=clip.streamer_id,
        input_path=clip.file_path,
        preset=payload.preset,
        watermark_text=viewer.username,
        subtitles_path=None,
    )
    clip.export_status = "queued"
    clip.export_preset = payload.preset
    clip.export_path = job.get("output_path")
    clip.export_updated_at = datetime.utcnow()

    action = ViewerAction(
        streamer_id=streamer_id,
        viewer_id=viewer.id,
        action_type="export_clip",
        target=str(clip.id),
        cost=cost,
        status="queued",
        payload={"preset": payload.preset},
    )
    db.add(action)

    insert_stream_event(
        db,
        streamer_id=streamer_id,
        platform="viewer",
        event_type="viewer_impact",
        user_id=str(viewer.id),
        username=viewer.username,
        message=f"Viewer redeemed export for clip {clip.id}",
        payload={"clip_id": clip.id, "preset": payload.preset},
    )

    db.commit()
    return {"status": "success", "credits": viewer.credits, "job": job}


@router.post("/api/viewer/sound")
def trigger_sound(payload: SoundRequest, request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    _enforce_limit(db, viewer, action_type="trigger_sound", limit_key="sound_actions_per_day", period="day")

    cost = 5
    if viewer.credits < cost:
        raise HTTPException(status_code=402, detail="Not enough credits")

    viewer.credits -= cost
    viewer.total_spent += cost

    action = ViewerAction(
        streamer_id=streamer_id,
        viewer_id=viewer.id,
        action_type="trigger_sound",
        target=payload.sound,
        cost=cost,
        status="queued",
    )
    db.add(action)

    insert_stream_event(
        db,
        streamer_id=streamer_id,
        platform="viewer",
        event_type="viewer_impact",
        user_id=str(viewer.id),
        username=viewer.username,
        message=f"Viewer triggered sound: {payload.sound}",
        payload={"sound": payload.sound},
    )

    db.commit()
    return {"status": "success", "credits": viewer.credits}


@router.post("/api/viewer/companion/analyze")
@limiter.limit("30/minute")
def companion_analyze(
    payload: CompanionAnalyzeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_viewer(request)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    _enforce_limit(db, viewer, action_type="ai_companion_ask", limit_key="ai_asks_per_day", period="day")

    text = (payload.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="message required")

    improved = _improve_question(text)
    normalized = _normalize_text(improved)
    window_since = datetime.now(timezone.utc) - timedelta(minutes=3)
    from backend.database.models.stream_event import StreamEvent
    recent = (
        db.query(StreamEvent)
        .filter(StreamEvent.streamer_id == streamer_id, StreamEvent.created_at >= window_since)
        .all()
    )
    message_rate = max(1, len(recent))
    duplicate_count = sum(1 for e in recent if _normalize_text(e.message or "") == normalized)
    timing_score = max(10, min(100, int(100 - (message_rate * 3))))
    notice_score = max(10, min(100, int(80 - duplicate_count * 12 + timing_score * 0.2)))

    recommendation = "send_now"
    if timing_score < 40:
        recommendation = "wait_for_quieter_moment"
    elif duplicate_count >= 3:
        recommendation = "already_trending_join_briefly"

    db.add(
        ViewerAction(
            streamer_id=streamer_id,
            viewer_id=viewer.id,
            action_type="ai_companion_ask",
            target=normalized[:180],
            cost=0,
            status="executed",
            payload={"timing_score": timing_score, "notice_score": notice_score},
        )
    )
    db.commit()

    return {
        "status": "success",
        "improved_message": improved,
        "timing_score": timing_score,
        "notice_score": notice_score,
        "duplicate_count_recent": duplicate_count,
        "recommendation": recommendation,
    }


@router.post("/api/viewer/companion/sent")
def companion_mark_sent(payload: CompanionSentRequest, request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    sent = (payload.sent_message or payload.original_message or "").strip()
    if not sent:
        raise HTTPException(status_code=400, detail="sent_message required")
    key = _normalize_text(sent)
    action = ViewerAction(
        streamer_id=streamer_id,
        viewer_id=viewer.id,
        action_type="companion_sent_question",
        target=key[:180],
        cost=0,
        status="queued",
        payload={
            "original_message": (payload.original_message or "")[:500],
            "sent_message": sent[:500],
            "normalized_key": key,
            "manual_answered": False,
        },
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return {"status": "success", "tracking_id": action.id}


@router.post("/api/viewer/companion/mark-answered")
def companion_mark_answered(payload: CompanionAnswerRequest, request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    action = (
        db.query(ViewerAction)
        .filter(ViewerAction.id == payload.tracking_id, ViewerAction.viewer_id == viewer.id)
        .first()
    )
    if not action:
        raise HTTPException(status_code=404, detail="Tracking record not found")
    current = action.payload or {}
    action.payload = {**current, "manual_answered": True}
    action.status = "executed"
    db.commit()
    return {"status": "success"}


@router.get("/api/viewer/companion/status")
def companion_status(tracking_id: int, request: Request, db: Session = Depends(get_db)):
    user = _require_viewer(request)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    action = (
        db.query(ViewerAction)
        .filter(ViewerAction.id == tracking_id, ViewerAction.viewer_id == viewer.id)
        .first()
    )
    if not action:
        raise HTTPException(status_code=404, detail="Tracking record not found")

    streamer = db.query(Streamer).filter(Streamer.id == action.streamer_id).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    payload = action.payload or {}
    if payload.get("manual_answered"):
        return {"status": "success", "state": "answered", "duplicate_count": 0}

    normalized_key = payload.get("normalized_key") or _normalize_text(action.target or "")
    created_at = action.created_at or datetime.now(timezone.utc)
    result = _companion_status(db, streamer, normalized_key, created_at)
    return {"status": "success", "state": result["status"], "duplicate_count": result["duplicate_count"], "elapsed_min": result["elapsed_min"]}


@router.post("/api/viewer/companion/retry-suggestion")
@limiter.limit("30/minute")
def companion_retry_suggestion(
    payload: CompanionRetryRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_viewer(request)
    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    action = (
        db.query(ViewerAction)
        .filter(ViewerAction.id == payload.tracking_id, ViewerAction.viewer_id == viewer.id)
        .first()
    )
    if not action:
        raise HTTPException(status_code=404, detail="Tracking record not found")

    msg = ((action.payload or {}).get("sent_message") or action.target or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="No source message found")

    from backend.database.models.stream_event import StreamEvent
    window_since = datetime.now(timezone.utc) - timedelta(minutes=3)
    recent_count = (
        db.query(StreamEvent)
        .filter(StreamEvent.streamer_id == action.streamer_id, StreamEvent.created_at >= window_since)
        .count()
    )
    timing_advice = "send_now" if recent_count < 20 else "wait_60_90_seconds"
    retry_message = _retry_variant(msg)

    current_payload = action.payload or {}
    action.payload = {
        **current_payload,
        "retry_message": retry_message,
        "retry_generated_at": datetime.now(timezone.utc).isoformat(),
        "retry_timing_advice": timing_advice,
    }
    db.commit()
    return {
        "status": "success",
        "retry_message": retry_message,
        "timing_advice": timing_advice,
        "recent_chat_rate_3m": recent_count,
    }


@router.get("/api/viewer/catchup/recap")
@limiter.limit("30/minute")
def catchup_recap(
    request: Request,
    db: Session = Depends(get_db),
    mode: str = "quick",
):
    viewer, streamer_id = _optional_viewer(request, db)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    window_since = datetime.now(timezone.utc) - timedelta(hours=3)
    rows = (
        db.query(StreamEvent)
        .filter(
            StreamEvent.streamer_id == streamer_id,
            StreamEvent.created_at >= window_since,
            StreamEvent.message.isnot(None),
        )
        .order_by(StreamEvent.created_at.asc())
        .limit(500)
        .all()
    )
    messages = [r.message or "" for r in rows]
    weighted_messages = _weighted_recent_messages(rows)
    platform_counts = Counter([(r.platform or "unknown") for r in rows])

    death_count = sum(1 for msg in weighted_messages if any(k in (msg or "").lower() for k in ["you died", "death", "rip", "dead"]))
    goal = _infer_goal(weighted_messages)
    mood = _infer_mood(weighted_messages)
    topics = _top_topics(weighted_messages, limit=3)
    dominant_platform = platform_counts.most_common(1)[0][0] if platform_counts else "unknown"

    if mode == "full":
        recap = (
            f"Current goal: {goal}. "
            f"Deaths so far: {death_count}. "
            f"Mood: {mood}. "
            f"Top topics: {', '.join(topics) if topics else 'none yet'}. "
            f"Main platform activity: {dominant_platform}."
        )
    else:
        recap = f"Current goal: {goal}. Deaths: {death_count}. Mood: {mood}."

    if viewer:
        db.add(
            ViewerAction(
                streamer_id=streamer_id,
                viewer_id=viewer.id,
                action_type="catchup_recap",
                target=f"!recap:{mode}",
                cost=0,
                status="executed",
                payload={"death_count": death_count, "mood": mood, "topics": topics, "platform_mix": dict(platform_counts)},
            )
        )
        db.commit()

    return {
        "status": "success",
        "mode": "full" if mode == "full" else "quick",
        "recap": recap,
        "goal": goal,
        "death_count": death_count,
        "mood": mood,
        "topics": topics,
        "platform_mix": dict(platform_counts),
        "dominant_platform": dominant_platform,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/viewer/catchup/highlights")
@limiter.limit("30/minute")
def catchup_highlights(
    payload: CatchupHighlightRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    viewer, streamer_id = _optional_viewer(request, db)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    limit = max(1, min(payload.limit or 3, 6))
    clips = (
        db.query(Clip)
        .filter(
            Clip.streamer_id == streamer_id,
            or_(Clip.status == "approved", Clip.status == "pending"),
        )
        .order_by(Clip.quality_score.desc().nullslast(), Clip.created_at.desc())
        .limit(limit)
        .all()
    )
    if not clips:
        clips = (
            db.query(Clip)
            .filter(Clip.streamer_id == streamer_id)
            .order_by(Clip.created_at.desc())
            .limit(limit)
            .all()
        )

    items = [
        {
            "id": c.id,
            "title": c.title or f"Highlight #{c.id}",
            "url": c.file_path,
            "thumbnail_url": c.thumbnail_path,
            "moment_label": (c.tags[0] if isinstance(c.tags, list) and c.tags else None),
            "status": c.status,
            "score": c.quality_score,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in clips
    ]
    if viewer:
        db.add(
            ViewerAction(
                streamer_id=streamer_id,
                viewer_id=viewer.id,
                action_type="catchup_highlights",
                target=f"top_{limit}",
                cost=0,
                status="executed",
            )
        )
        db.commit()
    return {"status": "success", "highlights": items}
