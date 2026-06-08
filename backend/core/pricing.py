import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.database.models.viewer_action import ViewerAction

PRICING_PATH = Path("backend/config/pricing.json")


def _load_pricing() -> dict[str, Any]:
    if not PRICING_PATH.exists():
        return {}
    with PRICING_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _viewer_plan_id(viewer_tier: str | None) -> str:
    tier = (viewer_tier or "free").lower().strip()
    if tier in {"plus", "premium", "vip"}:
        return "viewer_plus"
    return "viewer_free"


def get_viewer_plan(viewer_tier: str | None) -> dict[str, Any]:
    data = _load_pricing()
    plan_id = _viewer_plan_id(viewer_tier)
    for plan in data.get("plans", []):
        if plan.get("id") == plan_id:
            return plan
    return {"id": "viewer_free", "name": "Viewer Free", "limits": {}}


def get_viewer_limit(viewer_tier: str | None, limit_key: str, default: int | None = None) -> int | None:
    plan = get_viewer_plan(viewer_tier)
    value = (plan.get("limits") or {}).get(limit_key, default)
    return value if isinstance(value, int) else default


def _window_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def count_viewer_actions(
    db: Session,
    viewer_id: int,
    action_type: str,
    period: str = "day",
) -> int:
    start = _window_start(period)
    return (
        db.query(ViewerAction)
        .filter(
            ViewerAction.viewer_id == viewer_id,
            ViewerAction.action_type == action_type,
            ViewerAction.created_at >= start,
        )
        .count()
    )


def limit_violation(
    db: Session,
    viewer_id: int,
    viewer_tier: str | None,
    action_type: str,
    limit_key: str,
    period: str = "day",
) -> dict[str, Any] | None:
    limit = get_viewer_limit(viewer_tier, limit_key)
    if not limit:
        return None
    used = count_viewer_actions(db, viewer_id, action_type, period)
    if used < limit:
        return None
    plan = get_viewer_plan(viewer_tier)
    return {
        "code": "LIMIT_REACHED",
        "plan": plan.get("name", "Viewer Free"),
        "limit_key": limit_key,
        "used": used,
        "limit": limit,
        "period": period,
        "message": f"Limit reached ({used}/{limit}) for {limit_key.replace('_', ' ')}. Please try again later.",
    }
