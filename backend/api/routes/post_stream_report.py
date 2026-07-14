import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from groq import AsyncGroq
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.database.models.clip import Clip
from backend.database.models.command import Command
from backend.database.models.stream_event import StreamEvent
from backend.database.session import get_db

router = APIRouter()


def _require_streamer(request: Request, db: Session):
    user = get_current_user(request, required=True)
    if getattr(user, "role", None) != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    try:
        return int(streamer_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid streamer_id")


def _strip_json_fences(text: str) -> str:
    if not text:
        return ""
    s = text.strip()
    # Common patterns: ```json ... ``` or ``` ... ```
    if s.startswith("```"):
        s = s.lstrip("`")
    s = s.strip()
    # Remove leading 'json' token if present
    if s.lower().startswith("json"):
        s = s[4:].strip()
    # Remove trailing backticks if present
    if s.endswith("```"):
        s = s[: -3].strip()
    return s.strip()


def _safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    try:
        cleaned = _strip_json_fences(text)
        return json.loads(cleaned)
    except Exception:
        return None


def _choose_peak_moment(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        return {"moment": "Unable to determine peak moment from available data.", "timestamp": None}

    def score_row(r: Dict[str, Any]) -> float:
        msg = str(r.get("message") or "")
        et = str(r.get("event_type") or "")
        hype = any(t in msg.lower() for t in ["wow", "omg", "insane", "clutch", "clip", "gg", "lets go", "pog"])
        return (20.0 if hype else 0.0) + (len(msg) / 20.0) + (5.0 if et else 0.0)

    best = max(candidates, key=score_row)
    return {
        "moment": str(best.get("message") or "Peak moment identified."),
        "timestamp": best.get("created_at"),
    }


def _estimate_chat_energy(chat_events: List[Dict[str, Any]]) -> str:
    if not chat_events:
        return "low"

    joined = "\n".join([str(e.get("message") or "") for e in chat_events[-200:]]).lower()
    hype_tokens = ["wow", "omg", "insane", "clutch", "clip", "gg", "lets go", "pog", "lmao", "w"]
    hype_count = sum(1 for t in hype_tokens if t in joined)

    density = len(chat_events)
    if density >= 120 or hype_count >= 6:
        return "high"
    if density >= 40 or hype_count >= 3:
        return "medium"
    return "low"


@router.get("/api/streamer/director/post-stream-report")
async def post_stream_report(request: Request, hours: int = 6, db: Session = Depends(get_db)):
    # ---- Query ----
    streamer_id = _require_streamer(request, db)
    lookback = max(1, min(int(hours), 72))
    since = datetime.now(timezone.utc) - timedelta(hours=lookback)

    event_rows = (
        db.query(StreamEvent)
        .filter(StreamEvent.streamer_id == streamer_id, StreamEvent.created_at >= since)
        .order_by(StreamEvent.created_at.asc())
        .limit(2000)
        .all()
    )
    clip_rows = (
        db.query(Clip)
        .filter(Clip.streamer_id == streamer_id, Clip.created_at >= since)
        .order_by(Clip.created_at.asc())
        .limit(400)
        .all()
    )
    command_rows = (
        db.query(Command)
        .filter(Command.streamer_id == streamer_id, Command.created_at >= since)
        .order_by(Command.created_at.asc())
        .limit(800)
        .all()
    )

    event_count = len(event_rows)
    clip_count = len(clip_rows)

    # ---- Top chat moments ----
    chat_like: List[Dict[str, Any]] = []
    for row in event_rows:
        msg = row.message
        et = (row.event_type or "").lower()
        if msg and (et.startswith("chat") or et in {"chat_message", "viewer_msg"} or len(msg) >= 12):
            chat_like.append(
                {
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "event_type": row.event_type,
                    "message": msg,
                }
            )

    # Keep only the most recent / relevant candidates
    chat_like = sorted(
        chat_like,
        key=lambda r: (r.get("created_at") or ""),
        reverse=True,
    )[:40]

    peak = _choose_peak_moment(chat_like)
    chat_energy = _estimate_chat_energy(chat_like)

    # ---- Command history ----
    command_history: List[Dict[str, Any]] = []
    for cmd in command_rows[-60:]:
        command_history.append(
            {
                "created_at": cmd.created_at.isoformat() if cmd.created_at else None,
                "status": cmd.status,
                "intent": cmd.intent,
                "command_text": cmd.command_text,
            }
        )

    # ---- Groq call ----
    groq = AsyncGroq(api_key=getattr(__import__("os"), "environ", {}).get("GROQ_API_KEY"))

    # Fallback JSON required by user
    fallback = {
        "summary": "Stream data collected. Report generation encountered an issue.",
        "peak_moment": "Unable to determine peak moment from available data.",
        "chat_energy": "medium",
        "clips_saved": clip_count,
        "growth_insight": "Keep streaming consistently to build comparison data.",
        "next_stream_suggestion": "Consider engaging chat more during quieter moments.",
    }

    if not groq:
        return fallback

    system_prompt = (
        "You are Kazumi's Stream Director. You must return ONLY a valid JSON object with the requested fields. "
        "Do not include markdown, code fences, or any other text."
    )

    user_payload = {
        "streamer_id": streamer_id,
        "window_hours": lookback,
        "event_count": event_count,
        "clip_count": clip_count,
        "chat_energy_candidates": chat_energy,
        "peak_candidates": peak,
        "top_chat_moments": [
            {
                "created_at": c.get("created_at"),
                "message": c.get("message"),
            }
            for c in chat_like[:8]
        ],
        "command_history": command_history,
    }

    prompt = (
        "Analyze this stream window and produce a concise but insightful report.\n\n"
        f"DATA (JSON): {json.dumps(user_payload, ensure_ascii=False)}\n\n"
        "Return a JSON object with exactly these fields:\n"
        "- summary: a 3-sentence stream overview\n"
        "- peak_moment: the single best moment description with timestamp\n"
        "- chat_energy: one of: low, medium, high\n"
        "- clips_saved: a count\n"
        "- growth_insight: one sentence comparing to typical session\n"
        "- next_stream_suggestion: one actionable recommendation\n\n"
        "Constraints:\n"
        "- summary must be exactly 3 sentences.\n"
        "- peak_moment must include a timestamp.\n"
        "- chat_energy must be exactly one of low/medium/high.\n"
        "- clips_saved must be a number (int).\n"
        "- Return JSON only."
    )

    try:
        # Use faster 8B model (10x faster) with 15-second timeout
        completion = await asyncio.wait_for(
            groq.chat.completions.create(
                model="llama-3.1-8b-instant",  # Faster model for post-stream reports
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            ),
            timeout=15.0,  # 15-second timeout
        )

        raw = completion.choices[0].message.content or ""
        parsed = _safe_json_loads(raw)
        if not parsed:
            return fallback

        # Fill required fields defensively
        parsed_summary = parsed.get("summary")
        parsed_peak = parsed.get("peak_moment")
        parsed_energy = parsed.get("chat_energy")
        parsed_clips = parsed.get("clips_saved")
        parsed_growth = parsed.get("growth_insight")
        parsed_next = parsed.get("next_stream_suggestion")

        out = {
            "summary": parsed_summary if isinstance(parsed_summary, str) and parsed_summary.strip() else fallback["summary"],
            "peak_moment": parsed_peak if isinstance(parsed_peak, str) and parsed_peak.strip() else fallback["peak_moment"],
            "chat_energy": parsed_energy if parsed_energy in {"low", "medium", "high"} else fallback["chat_energy"],
            "clips_saved": (
                int(parsed_clips) if isinstance(parsed_clips, (int, float, str)) and str(parsed_clips).strip().isdigit() else clip_count
            ),
            "growth_insight": parsed_growth if isinstance(parsed_growth, str) and parsed_growth.strip() else fallback["growth_insight"],
            "next_stream_suggestion": parsed_next if isinstance(parsed_next, str) and parsed_next.strip() else fallback["next_stream_suggestion"],
        }
        return out
    except Exception:
        return fallback

