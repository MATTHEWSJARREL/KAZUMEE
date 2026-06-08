from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.core.policy import DEFAULT_POLICY, get_policy_for_streamer
from backend.database.session import SessionLocal
from backend.database.models.streamer import Streamer

router = APIRouter(prefix="/policy", tags=["Policy"])


class PolicyUpdateRequest(BaseModel):
    policy: dict


@router.get("")
async def get_policy(request: Request):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")

    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        overrides = streamer.policy_json if streamer and streamer.policy_json else {}
        return {
            "status": "success",
            "policy": get_policy_for_streamer(streamer_id),
            "overrides": overrides,
        }
    finally:
        db.close()


@router.put("")
async def update_policy(request: Request, payload: PolicyUpdateRequest):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")

    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    allowed_values = {"allow", "approve", "deny"}
    cleaned = {}
    for key, value in (payload.policy or {}).items():
        if key in DEFAULT_POLICY and value in allowed_values:
            cleaned[key] = value

    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        if not streamer:
            return {"status": "error", "message": "streamer not found"}
        streamer.policy_json = cleaned
        db.commit()
        return {"status": "success", "policy": get_policy_for_streamer(streamer_id)}
    finally:
        db.close()
