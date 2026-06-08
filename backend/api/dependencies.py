from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.core.entitlements import is_viewer_feature
from backend.database.models.streamer import Streamer
from backend.database.session import get_db


TIER_FEATURES: dict[str, set[str]] = {
    "free": {
        "viewer_basics",
    },
    "creator": {
        "viewer_basics",
        "catchup_companion",
        "ask_zumi",
    },
    "pro": {
        "viewer_basics",
        "catchup_companion",
        "ask_zumi",
        "backseat_gaming",
        "obs_source_control",
    },
}


def get_current_streamer(
    request: Request,
    db: Session = Depends(get_db),
) -> Streamer:
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    try:
        streamer_id_int = int(streamer_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="invalid streamer_id")
    streamer = db.query(Streamer).filter(Streamer.id == streamer_id_int).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return streamer


def require_feature(feature: str):
    def _dependency(streamer: Streamer = Depends(get_current_streamer)) -> Streamer:
        if is_viewer_feature(feature):
            return streamer
        tier = str(streamer.subscription_tier or "free").strip().lower() or "free"
        allowed = TIER_FEATURES.get(tier, TIER_FEATURES["free"])
        if feature not in allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "UPGRADE_REQUIRED",
                    "feature": feature,
                    "current_tier": tier,
                },
            )
        return streamer

    return _dependency
