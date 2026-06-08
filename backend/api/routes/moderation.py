from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import re
from typing import Optional, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.core.event_store import insert_stream_event
from backend.core.logger import get_logger
from backend.database.session import SessionLocal

router = APIRouter()
log = get_logger("Moderation")

MILD_TOXIC_KEYWORDS = {
    "stupid", "idiot", "trash", "garbage", "pathetic", "loser", "dumb", "hate",
}
SEVERE_TOXIC_KEYWORDS = {
    "kill yourself", "kys", "die", "racial slur", "threat", "doxx", "swat",
}


class ModerationRequest(BaseModel):
    user_id: str
    username: str
    message: str
    action: Optional[str] = None  # warn, timeout, ban, allow
    platform: str = "twitch"


class ModerationResponse(BaseModel):
    case_id: Optional[str] = None
    action_taken: str
    reason: str
    user_id: str
    username: str
    severity: str
    confidence: float
    queued_for_review: bool


class ModerationReviewRequest(BaseModel):
    action: str  # allow | warn | timeout | ban
    notes: Optional[str] = None


class ModerationActionBundleRequest(BaseModel):
    case_id: str
    bundle: str  # warn_only | timeout_purge | nuke_user
    notes: Optional[str] = None
    duration_seconds: int = 600


class PanicShieldRequest(BaseModel):
    enabled: bool = True
    safe_scene: str = "BRB"
    follower_only_minutes: int = 10
    slow_mode_seconds: int = 5
    reason: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_moderation_table(db):
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS moderation_cases (
                id varchar(32) PRIMARY KEY,
                status varchar(16) NOT NULL,
                streamer_id integer NOT NULL,
                platform varchar(32) NOT NULL,
                username varchar(255) NOT NULL,
                user_id varchar(255),
                message text NOT NULL,
                confidence double precision NOT NULL,
                severity varchar(16) NOT NULL,
                recommended_action varchar(16) NOT NULL,
                proposed_action varchar(16) NOT NULL,
                final_action varchar(16),
                reason text NOT NULL,
                created_at timestamptz NOT NULL,
                reviewed_at timestamptz,
                review_notes text,
                reviewer varchar(255)
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_moderation_cases_streamer_status ON moderation_cases(streamer_id, status)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_moderation_cases_created_at ON moderation_cases(created_at)"))
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS moderation_audit_logs (
                id bigserial PRIMARY KEY,
                streamer_id integer NOT NULL,
                case_id varchar(32),
                actor_email varchar(255),
                action varchar(64) NOT NULL,
                bundle varchar(64),
                target_user varchar(255),
                target_user_id varchar(255),
                details text,
                created_at timestamptz NOT NULL
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_moderation_audit_streamer_created ON moderation_audit_logs(streamer_id, created_at DESC)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_moderation_audit_case_id ON moderation_audit_logs(case_id)"))
    db.commit()


def _serialize_case_row(row) -> dict:
    created_at = row["created_at"]
    reviewed_at = row["reviewed_at"]
    return {
        "id": row["id"],
        "status": row["status"],
        "streamer_id": row["streamer_id"],
        "platform": row["platform"],
        "username": row["username"],
        "user_id": row["user_id"],
        "message": row["message"],
        "confidence": float(row["confidence"]),
        "severity": row["severity"],
        "recommended_action": row["recommended_action"],
        "proposed_action": row["proposed_action"],
        "final_action": row["final_action"],
        "reason": row["reason"],
        "created_at": created_at.isoformat() if created_at else None,
        "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
        "review_notes": row["review_notes"],
        "reviewer": row["reviewer"],
    }


def _serialize_audit_row(row) -> dict:
    created_at = row["created_at"]
    details_raw = row["details"]
    details = None
    if details_raw:
        try:
            details = json.loads(details_raw)
        except Exception:
            details = {"raw": details_raw}
    return {
        "id": int(row["id"]),
        "streamer_id": int(row["streamer_id"]),
        "case_id": row["case_id"],
        "actor_email": row["actor_email"],
        "action": row["action"],
        "bundle": row["bundle"],
        "target_user": row["target_user"],
        "target_user_id": row["target_user_id"],
        "details": details,
        "created_at": created_at.isoformat() if created_at else None,
    }


def _write_audit_log(
    db,
    *,
    streamer_id: int,
    action: str,
    actor_email: Optional[str],
    case_id: Optional[str] = None,
    bundle: Optional[str] = None,
    target_user: Optional[str] = None,
    target_user_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
):
    db.execute(
        text(
            """
            INSERT INTO moderation_audit_logs (
                streamer_id, case_id, actor_email, action, bundle, target_user, target_user_id, details, created_at
            ) VALUES (
                :streamer_id, :case_id, :actor_email, :action, :bundle, :target_user, :target_user_id, :details, :created_at
            )
            """
        ),
        {
            "streamer_id": streamer_id,
            "case_id": case_id,
            "actor_email": actor_email,
            "action": action,
            "bundle": bundle,
            "target_user": target_user,
            "target_user_id": target_user_id,
            "details": json.dumps(details or {}),
            "created_at": datetime.now(timezone.utc),
        },
    )


def _score_message(message: str) -> tuple[float, str, str]:
    text_value = (message or "").lower().strip()
    if not text_value:
        return 0.0, "low", "Empty message"

    non_targeted_hate = bool(
        re.search(r"\bi\s+hate\s+(this|that|the)\s+(level|boss|game|map|quest|puzzle)\b", text_value)
        or re.search(r"\bthis\s+(level|boss|game|map|quest|puzzle)\s+is\s+(awful|trash|bad|annoying)\b", text_value)
    )

    score = 0.0
    reasons: list[str] = []

    severe_hits = [k for k in SEVERE_TOXIC_KEYWORDS if k in text_value]
    mild_hits = [k for k in MILD_TOXIC_KEYWORDS if k in text_value]
    if non_targeted_hate:
        mild_hits = [k for k in mild_hits if k != "hate"]
        reasons.append("context indicates non-targeted frustration")
    if severe_hits:
        score += 0.75
        reasons.append(f"severe terms: {', '.join(severe_hits[:2])}")
    if mild_hits:
        score += min(0.35, 0.12 * len(mild_hits))
        reasons.append(f"toxic terms: {', '.join(mild_hits[:3])}")

    words = re.findall(r"\b\w+\b", message)
    if words:
        caps_words = sum(1 for w in words if len(w) > 2 and w.isupper())
        caps_ratio = caps_words / len(words)
        if caps_ratio >= 0.6:
            score += 0.15
            reasons.append("excessive uppercase")

    if re.search(r"[!?]{3,}", message):
        score += 0.08
        reasons.append("excessive punctuation")

    if re.search(r"(.)\1{5,}", message.lower()):
        score += 0.07
        reasons.append("spam-like repeated characters")

    score = min(score, 1.0)
    if score >= 0.85:
        severity = "critical"
    elif score >= 0.65:
        severity = "high"
    elif score >= 0.4:
        severity = "medium"
    else:
        severity = "low"

    reason = ", ".join(reasons) if reasons else "Message appears clean"
    return score, severity, reason


def _recommended_action(score: float) -> str:
    if score >= 0.85:
        return "ban"
    if score >= 0.65:
        return "timeout"
    if score >= 0.4:
        return "warn"
    return "allow"


def _log_moderation_event(
    streamer_id: Optional[int],
    platform: str,
    event_type: str,
    username: str,
    message: str,
    payload: dict,
):
    if not streamer_id:
        return
    db = SessionLocal()
    try:
        insert_stream_event(
            db,
            streamer_id=streamer_id,
            platform=platform or "twitch",
            event_type=event_type,
            user_id=None,
            username=username,
            message=message,
            payload=payload,
        )
        db.commit()
    finally:
        db.close()


@router.post("/moderate", response_model=ModerationResponse)
async def moderate_message(payload: ModerationRequest, request: Request):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    score, severity, reason = _score_message(payload.message)
    auto_action = _recommended_action(score)
    action = payload.action if payload.action in {"allow", "warn", "timeout", "ban"} else auto_action

    queued = action in {"warn", "timeout", "ban"}
    case_id = str(uuid4())[:8] if queued else None

    db = SessionLocal()
    try:
        _ensure_moderation_table(db)
        if queued:
            db.execute(
                text(
                    """
                    INSERT INTO moderation_cases (
                        id, status, streamer_id, platform, username, user_id, message, confidence,
                        severity, recommended_action, proposed_action, final_action, reason,
                        created_at, reviewed_at, review_notes, reviewer
                    ) VALUES (
                        :id, :status, :streamer_id, :platform, :username, :user_id, :message, :confidence,
                        :severity, :recommended_action, :proposed_action, NULL, :reason,
                        :created_at, NULL, NULL, NULL
                    )
                    """
                ),
                {
                    "id": case_id,
                    "status": "pending",
                    "streamer_id": streamer_id,
                    "platform": payload.platform,
                    "username": payload.username,
                    "user_id": payload.user_id,
                    "message": payload.message,
                    "confidence": round(score, 3),
                    "severity": severity,
                    "recommended_action": auto_action,
                    "proposed_action": action,
                    "reason": reason,
                    "created_at": datetime.now(timezone.utc),
                },
            )
            db.commit()
            _write_audit_log(
                db,
                streamer_id=streamer_id,
                action="case_queued",
                actor_email=user.email,
                case_id=case_id,
                bundle=None,
                target_user=payload.username,
                target_user_id=payload.user_id,
                details={
                    "proposed_action": action,
                    "recommended_action": auto_action,
                    "severity": severity,
                    "confidence": round(score, 3),
                },
            )
            db.commit()
            _log_moderation_event(
                streamer_id=streamer_id,
                platform=payload.platform,
                event_type="moderation_flagged",
                username=payload.username,
                message=payload.message,
                payload={
                    "case_id": case_id,
                    "severity": severity,
                    "confidence": round(score, 3),
                    "reason": reason,
                    "recommended_action": auto_action,
                },
            )
            log.warning("Queued moderation case %s for %s (%s)", case_id, payload.username, action)
        else:
            _write_audit_log(
                db,
                streamer_id=streamer_id,
                action="message_allowed",
                actor_email=user.email,
                case_id=None,
                target_user=payload.username,
                target_user_id=payload.user_id,
                details={"confidence": round(score, 3), "severity": severity},
            )
            db.commit()
            _log_moderation_event(
                streamer_id=streamer_id,
                platform=payload.platform,
                event_type="moderation_allowed",
                username=payload.username,
                message=payload.message,
                payload={"confidence": round(score, 3), "reason": reason},
            )
            log.info("Message approved for %s", payload.username)

        return ModerationResponse(
            case_id=case_id,
            action_taken=action,
            reason=reason if queued else "Message approved",
            user_id=payload.user_id,
            username=payload.username,
            severity=severity,
            confidence=round(score, 3),
            queued_for_review=queued,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Moderation error")
        raise HTTPException(status_code=500, detail=f"Moderation failed: {str(exc)}")
    finally:
        db.close()


@router.get("/cases")
async def list_moderation_cases(request: Request, status: str = "pending", limit: int = 50):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    status_value = status if status in {"pending", "resolved"} else "pending"
    safe_limit = max(1, min(limit, 200))

    db = SessionLocal()
    try:
        _ensure_moderation_table(db)
        rows = db.execute(
            text(
                """
                SELECT
                    id, status, streamer_id, platform, username, user_id, message, confidence,
                    severity, recommended_action, proposed_action, final_action, reason,
                    created_at, reviewed_at, review_notes, reviewer
                FROM moderation_cases
                WHERE streamer_id = :streamer_id
                  AND status = :status
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"streamer_id": streamer_id, "status": status_value, "limit": safe_limit},
        ).mappings().all()
        cases = [_serialize_case_row(row) for row in rows]

        count_row = db.execute(
            text(
                """
                SELECT count(*) AS count
                FROM moderation_cases
                WHERE streamer_id = :streamer_id
                  AND status = :status
                """
            ),
            {"streamer_id": streamer_id, "status": status_value},
        ).mappings().first()
        count = int(count_row["count"]) if count_row else 0

        return {"cases": cases, "count": count}
    finally:
        db.close()


@router.get("/queue")
async def moderation_triage_queue(request: Request, limit: int = 50):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    safe_limit = max(1, min(limit, 200))

    db = SessionLocal()
    try:
        _ensure_moderation_table(db)
        rows = db.execute(
            text(
                """
                SELECT
                    id, status, streamer_id, platform, username, user_id, message, confidence,
                    severity, recommended_action, proposed_action, final_action, reason,
                    created_at, reviewed_at, review_notes, reviewer
                FROM moderation_cases
                WHERE streamer_id = :streamer_id
                  AND status = 'pending'
                ORDER BY confidence DESC, created_at DESC
                LIMIT :limit
                """
            ),
            {"streamer_id": streamer_id, "limit": safe_limit},
        ).mappings().all()

        severity_counts = Counter(row["severity"] for row in rows)
        action_counts = Counter(row["proposed_action"] for row in rows)
        return {
            "queue": [_serialize_case_row(row) for row in rows],
            "summary": {
                "pending_total": len(rows),
                "by_severity": dict(severity_counts),
                "by_proposed_action": dict(action_counts),
            },
        }
    finally:
        db.close()


@router.post("/bundles/apply")
async def apply_action_bundle(payload: ModerationActionBundleRequest, request: Request):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    bundle = (payload.bundle or "").strip().lower()
    if bundle not in {"warn_only", "timeout_purge", "nuke_user"}:
        raise HTTPException(status_code=400, detail="bundle must be warn_only, timeout_purge, or nuke_user")

    db = SessionLocal()
    try:
        _ensure_moderation_table(db)
        case_row = db.execute(
            text(
                """
                SELECT
                    id, status, streamer_id, platform, username, user_id, message, confidence,
                    severity, recommended_action, proposed_action, final_action, reason,
                    created_at, reviewed_at, review_notes, reviewer
                FROM moderation_cases
                WHERE id = :id
                LIMIT 1
                """
            ),
            {"id": payload.case_id},
        ).mappings().first()
        if not case_row:
            raise HTTPException(status_code=404, detail="Case not found")
        if int(case_row["streamer_id"]) != streamer_id:
            raise HTTPException(status_code=403, detail="Case does not belong to this streamer")

        final_action = "warn"
        bundle_steps: list[str] = []
        if bundle == "warn_only":
            final_action = "warn"
            bundle_steps = ["warn user"]
        elif bundle == "timeout_purge":
            final_action = "timeout"
            bundle_steps = ["timeout user", "purge recent messages (last 30s)"]
        elif bundle == "nuke_user":
            final_action = "ban"
            bundle_steps = ["delete source message", "ban user", "purge recent messages (last 30s)"]

        executor_result: Optional[dict[str, Any]] = None
        executor = getattr(request.app.state, "executor", None)
        if executor and final_action in {"timeout", "ban"}:
            run_result = await executor.execute(
                "moderation_auto_action",
                {
                    "action": final_action,
                    "streamer_id": streamer_id,
                    "username": case_row["username"],
                    "user_id": case_row["user_id"],
                    "duration_seconds": int(payload.duration_seconds or 600),
                    "reason": payload.notes or "Kazumi moderation action bundle",
                },
            )
            executor_result = {
                "status": run_result.status,
                "message": run_result.message,
                "data": run_result.data,
            }

        reviewed_at = datetime.now(timezone.utc)
        note_suffix = f" [bundle:{bundle}]"
        combined_notes = f"{(payload.notes or '').strip()}{note_suffix}".strip()

        db.execute(
            text(
                """
                UPDATE moderation_cases
                SET
                    status = 'resolved',
                    final_action = :final_action,
                    reviewed_at = :reviewed_at,
                    review_notes = :review_notes,
                    reviewer = :reviewer
                WHERE id = :id
                """
            ),
            {
                "id": payload.case_id,
                "final_action": final_action,
                "reviewed_at": reviewed_at,
                "review_notes": combined_notes,
                "reviewer": user.email,
            },
        )
        _write_audit_log(
            db,
            streamer_id=streamer_id,
            action="bundle_applied",
            actor_email=user.email,
            case_id=payload.case_id,
            bundle=bundle,
            target_user=case_row["username"],
            target_user_id=case_row["user_id"],
            details={
                "steps": bundle_steps,
                "final_action": final_action,
                "executor_result": executor_result,
                "notes": payload.notes or "",
            },
        )
        db.commit()

        _log_moderation_event(
            streamer_id=streamer_id,
            platform=case_row["platform"] or "twitch",
            event_type="moderation_bundle_applied",
            username=case_row["username"] or "",
            message=case_row["message"] or "",
            payload={
                "case_id": payload.case_id,
                "bundle": bundle,
                "final_action": final_action,
                "steps": bundle_steps,
                "executor_result": executor_result,
            },
        )

        refreshed_case = db.execute(
            text(
                """
                SELECT
                    id, status, streamer_id, platform, username, user_id, message, confidence,
                    severity, recommended_action, proposed_action, final_action, reason,
                    created_at, reviewed_at, review_notes, reviewer
                FROM moderation_cases
                WHERE id = :id
                LIMIT 1
                """
            ),
            {"id": payload.case_id},
        ).mappings().first()

        return {
            "status": "success",
            "bundle": bundle,
            "case": _serialize_case_row(refreshed_case) if refreshed_case else None,
            "steps": bundle_steps,
            "executor_result": executor_result,
        }
    finally:
        db.close()


@router.post("/panic")
async def toggle_panic_shield(payload: PanicShieldRequest, request: Request):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    db = SessionLocal()
    try:
        _ensure_moderation_table(db)
        executor = getattr(request.app.state, "executor", None)
        if payload.enabled and not executor:
            raise HTTPException(status_code=503, detail="Executor unavailable")

        panic_result = None
        shield_result = None
        status = "deactivated"
        if payload.enabled:
            status = "activated"
            panic = await executor.execute("panic_mode", {"panic_scene": payload.safe_scene})
            shield = await executor.execute(
                "lock_chat_follower_only",
                {
                    "streamer_id": streamer_id,
                    "follower_only_minutes": max(0, int(payload.follower_only_minutes)),
                    "slow_mode_seconds": max(3, int(payload.slow_mode_seconds)),
                },
            )
            panic_result = {"status": panic.status, "message": panic.message, "data": panic.data}
            shield_result = {"status": shield.status, "message": shield.message, "data": shield.data}

        _write_audit_log(
            db,
            streamer_id=streamer_id,
            action="panic_toggle",
            actor_email=user.email,
            bundle="panic_shield",
            details={
                "status": status,
                "safe_scene": payload.safe_scene,
                "follower_only_minutes": payload.follower_only_minutes,
                "slow_mode_seconds": payload.slow_mode_seconds,
                "panic_result": panic_result,
                "shield_result": shield_result,
                "reason": payload.reason or "",
            },
        )
        db.commit()

        _log_moderation_event(
            streamer_id=streamer_id,
            platform="twitch",
            event_type="moderation_panic_toggle",
            username="Kazumi",
            message=f"Panic shield {status}",
            payload={
                "status": status,
                "safe_scene": payload.safe_scene,
                "panic_result": panic_result,
                "shield_result": shield_result,
            },
        )

        return {
            "status": "success",
            "panic": status,
            "panic_result": panic_result,
            "shield_result": shield_result,
        }
    finally:
        db.close()


@router.post("/cases/{case_id}/review")
async def review_case(case_id: str, payload: ModerationReviewRequest, request: Request):
    if payload.action not in {"allow", "warn", "timeout", "ban"}:
        raise HTTPException(status_code=400, detail="Invalid action")

    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    db = SessionLocal()
    try:
        _ensure_moderation_table(db)
        row = db.execute(
            text(
                """
                SELECT streamer_id FROM moderation_cases
                WHERE id = :id
                LIMIT 1
                """
            ),
            {"id": case_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Case not found")
        if int(row["streamer_id"]) != streamer_id:
            raise HTTPException(status_code=403, detail="Case does not belong to this streamer")

        reviewed_at = datetime.now(timezone.utc)
        db.execute(
            text(
                """
                UPDATE moderation_cases
                SET
                    status = 'resolved',
                    final_action = :final_action,
                    reviewed_at = :reviewed_at,
                    review_notes = :review_notes,
                    reviewer = :reviewer
                WHERE id = :id
                """
            ),
            {
                "id": case_id,
                "final_action": payload.action,
                "reviewed_at": reviewed_at,
                "review_notes": payload.notes or "",
                "reviewer": user.email,
            },
        )
        db.commit()

        case_row = db.execute(
            text(
                """
                SELECT
                    id, status, streamer_id, platform, username, user_id, message, confidence,
                    severity, recommended_action, proposed_action, final_action, reason,
                    created_at, reviewed_at, review_notes, reviewer
                FROM moderation_cases
                WHERE id = :id
                LIMIT 1
                """
            ),
            {"id": case_id},
        ).mappings().first()

        _log_moderation_event(
            streamer_id=streamer_id,
            platform=(case_row["platform"] if case_row else "twitch"),
            event_type="moderation_reviewed",
            username=(case_row["username"] if case_row else ""),
            message=(case_row["message"] if case_row else ""),
            payload={
                "case_id": case_id,
                "final_action": payload.action,
                "review_notes": payload.notes or "",
                "reviewed_at": reviewed_at.isoformat(),
            },
        )
        # Write audit log in same transaction as case update
        _write_audit_log(
            db,
            streamer_id=streamer_id,
            action="case_reviewed",
            actor_email=user.email,
            case_id=case_id,
            target_user=(case_row["username"] if case_row else None),
            target_user_id=(case_row["user_id"] if case_row else None),
            details={
                "final_action": payload.action,
                "notes": payload.notes or "",
            },
        )
        # Single commit for both case and audit
        db.commit()
        return {"status": "success", "case": _serialize_case_row(case_row) if case_row else None}
    finally:
        db.close()


@router.get("/audit")
async def moderation_audit_log(request: Request, limit: int = 100, case_id: Optional[str] = None):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    safe_limit = max(1, min(limit, 200))

    db = SessionLocal()
    try:
        _ensure_moderation_table(db)
        params: dict[str, Any] = {"streamer_id": streamer_id, "limit": safe_limit}
        where_clause = "WHERE streamer_id = :streamer_id"
        if case_id:
            where_clause += " AND case_id = :case_id"
            params["case_id"] = case_id

        rows = db.execute(
            text(
                f"""
                SELECT
                    id, streamer_id, case_id, actor_email, action, bundle, target_user, target_user_id, details, created_at
                FROM moderation_audit_logs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()

        return {"entries": [_serialize_audit_row(row) for row in rows], "count": len(rows)}
    finally:
        db.close()


@router.get("/metrics")
async def moderation_metrics(request: Request, hours: int = 24):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    lookback = max(1, min(hours, 168))
    since = datetime.now(timezone.utc) - timedelta(hours=lookback)

    db = SessionLocal()
    try:
        _ensure_moderation_table(db)
        rows = db.execute(
            text(
                """
                SELECT status, proposed_action, final_action, created_at
                FROM moderation_cases
                WHERE streamer_id = :streamer_id
                  AND created_at >= :since
                """
            ),
            {"streamer_id": streamer_id, "since": since},
        ).mappings().all()

        resolved = [r for r in rows if r["status"] == "resolved"]
        action_counts = Counter((r["final_action"] or r["proposed_action"] or "allow") for r in rows)
        total = len(rows)

        return {
            "window_hours": lookback,
            "flagged_total": total,
            "pending": sum(1 for r in rows if r["status"] == "pending"),
            "resolved": len(resolved),
            "resolution_rate": round((len(resolved) / total) * 100, 1) if total else 0.0,
            "actions": dict(action_counts),
        }
    finally:
        db.close()
