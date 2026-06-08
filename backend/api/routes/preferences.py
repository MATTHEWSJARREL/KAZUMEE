from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.database.models.streamer import Streamer
from backend.core.auth import get_current_user, resolve_streamer_id
from backend.core.taste import PRESET_PROFILES, apply_preset

router = APIRouter()


class PresetRequest(BaseModel):
    preset: str


@router.get("/api/preferences/presets")
def list_presets():
    return {
        "presets": [
            {"name": key, "description": value.get("description", "")}
            for key, value in PRESET_PROFILES.items()
        ]
    }


@router.get("/api/preferences")
def get_preferences(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return {"preferences": streamer.taste_profile or {}}


@router.post("/api/preferences/preset")
def set_preset(payload: PresetRequest, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    preset = payload.preset.lower().strip()
    if preset not in PRESET_PROFILES and preset != "balanced":
        raise HTTPException(status_code=400, detail="Invalid preset")

    streamer.taste_profile = apply_preset(streamer.taste_profile, preset)
    db.commit()
    return {"status": "success", "preset": preset, "preferences": streamer.taste_profile}
