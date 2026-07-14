from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.database.session import get_db
from backend.database.models.streamer import Streamer

router = APIRouter(prefix="/api/streamer/onboarding", tags=["Onboarding"])


class OnboardingCompleteRequest(BaseModel):
    pass


@router.post("/complete", response_model=None)
def complete_onboarding(
    request: Request,
    db: Session = Depends(get_db),
    payload: OnboardingCompleteRequest | None = None,
):
    _ = payload
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")

    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    streamer.onboarding_complete = True
    db.add(streamer)
    db.commit()
    return {"status": "success"}