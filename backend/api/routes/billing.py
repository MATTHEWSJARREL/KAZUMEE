import hashlib
import hmac
import json
import os

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database.models.streamer import Streamer
from backend.database.models.user import User
from backend.database.session import SessionLocal


router = APIRouter(prefix="/integrations/billing", tags=["Billing"])


def _extract_event_name(payload: dict) -> str:
    meta = payload.get("meta") or {}
    return str(meta.get("event_name") or payload.get("event_name") or payload.get("type") or "").strip().lower()


def _extract_user_email(payload: dict) -> str:
    data = payload.get("data") or {}
    attrs = data.get("attributes") or {}
    candidates = [
        attrs.get("user_email"),
        attrs.get("customer_email"),
        attrs.get("email"),
        data.get("user_email"),
        payload.get("user_email"),
    ]
    for candidate in candidates:
        value = str(candidate or "").strip().lower()
        if value:
            return value
    return ""


def _infer_subscription_tier(payload: dict) -> str:
    data = payload.get("data") or {}
    attrs = data.get("attributes") or {}
    custom_data = attrs.get("custom_data") or {}
    explicit_tier = str(
        custom_data.get("subscription_tier")
        or custom_data.get("tier")
        or attrs.get("tier")
        or ""
    ).strip().lower()
    if explicit_tier in {"free", "creator", "pro"}:
        return explicit_tier

    descriptor = " ".join(
        [
            str(attrs.get("variant_name") or ""),
            str(attrs.get("product_name") or ""),
            str(attrs.get("variant_id") or ""),
        ]
    ).lower()
    if "pro" in descriptor:
        return "pro"
    if "creator" in descriptor:
        return "creator"
    return "free"


def _lookup_streamer_by_email(db: Session, user_email: str) -> Streamer | None:
    if not user_email:
        return None
    streamer = (
        db.query(Streamer)
        .join(User, Streamer.user_id == User.id)
        .filter(User.email == user_email)
        .first()
    )
    if streamer:
        return streamer
    return (
        db.query(Streamer)
        .filter(Streamer.username == user_email)
        .first()
    )


def update_streamer_tier(
    db: Session,
    *,
    user_email: str,
    subscription_tier: str,
    subscription_status: str,
    subscription_will_cancel: bool | None = None,
) -> Streamer | None:
    streamer = _lookup_streamer_by_email(db, user_email)
    if not streamer:
        return None

    streamer.subscription_tier = subscription_tier
    streamer.subscription_status = subscription_status
    if subscription_will_cancel is not None:
        streamer.subscription_will_cancel = bool(subscription_will_cancel)
    db.commit()
    db.refresh(streamer)
    return streamer


@router.post("/webhook")
async def billing_webhook(request: Request):
    secret = (os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET") or "").strip()
    if not secret:
        raise HTTPException(status_code=500, detail="Billing webhook secret not configured")

    body = await request.body()
    signature = (request.headers.get("X-Signature") or "").strip()
    expected_signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_name = _extract_event_name(payload)
    user_email = _extract_user_email(payload)
    if not event_name:
        raise HTTPException(status_code=400, detail="Missing event name")

    db = SessionLocal()
    try:
        if event_name in {"subscription_created", "subscription_updated"}:
            attrs = (payload.get("data") or {}).get("attributes") or {}
            status = str(attrs.get("status") or "active").strip().lower() or "active"
            will_cancel = bool(
                attrs.get("cancelled")
                or attrs.get("cancel_at_period_end")
                or attrs.get("subscription_will_cancel")
            )
            tier = _infer_subscription_tier(payload)
            streamer = update_streamer_tier(
                db,
                user_email=user_email,
                subscription_tier=tier,
                subscription_status=status,
                subscription_will_cancel=will_cancel,
            )
            if not streamer:
                raise HTTPException(status_code=500, detail="Streamer not found for billing event")
            return {
                "status": "ok",
                "event": event_name,
                "updated": bool(streamer),
                "streamer_id": streamer.id if streamer else None,
                "tier": tier,
            }

        if event_name == "subscription_cancelled":
            streamer = _lookup_streamer_by_email(db, user_email)
            if streamer:
                streamer.subscription_will_cancel = True
                db.commit()
                db.refresh(streamer)
            return {
                "status": "ok",
                "event": event_name,
                "updated": bool(streamer),
                "streamer_id": streamer.id if streamer else None,
            }

        if event_name == "subscription_expired":
            streamer = update_streamer_tier(
                db,
                user_email=user_email,
                subscription_tier="free",
                subscription_status="inactive",
                subscription_will_cancel=False,
            )
            return {
                "status": "ok",
                "event": event_name,
                "updated": bool(streamer),
                "streamer_id": streamer.id if streamer else None,
            }

        return {"status": "ignored", "event": event_name}
    finally:
        db.close()

