"""
Custom Danger Phrases Management API
POST /api/irl/phrases - Add a custom danger phrase
DELETE /api/irl/phrases/{phrase_id} - Remove a custom danger phrase
GET /api/irl/phrases - List all custom danger phrases
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import uuid
import hashlib

from backend.api.dependencies import get_current_user, get_db
from backend.database.models import Streamer, StreamerCustomPhrase
from backend.core.logger import get_logger

router = APIRouter()
logger = get_logger("IRLPhrasesAPI")


class CustomPhraseRequest(BaseModel):
    """Request body for adding a custom danger phrase"""
    phrase: str
    sensitivity: float = 0.8  # 0.0-1.0, higher = more sensitive


class CustomPhraseResponse(BaseModel):
    """Response body for a custom phrase"""
    id: str
    phrase: str
    sensitivity: float
    created_at: str

    class Config:
        from_attributes = True


def _get_streamer(request, db: Session):
    """Helper to get current streamer"""
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")

    streamer = db.query(Streamer).filter(Streamer.user_id == user.id).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    return streamer


@router.post("/api/irl/phrases", response_model=CustomPhraseResponse)
def add_custom_phrase(
    payload: CustomPhraseRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Add a custom danger phrase to IRL safety monitoring.
    
    The phrase will trigger the same safety response as built-in phrases.
    Sensitivity ranges from 0.0 (very loose matching) to 1.0 (exact match only).
    
    Example:
        POST /api/irl/phrases
        {
            "phrase": "getting tired",
            "sensitivity": 0.85
        }
    """
    streamer = _get_streamer(request, db)

    # Validate input
    if not payload.phrase or len(payload.phrase.strip()) == 0:
        raise HTTPException(status_code=400, detail="Phrase cannot be empty")

    if len(payload.phrase) > 200:
        raise HTTPException(status_code=400, detail="Phrase too long (max 200 chars)")

    if not (0.0 <= payload.sensitivity <= 1.0):
        raise HTTPException(status_code=400, detail="Sensitivity must be between 0.0 and 1.0")

    # Check if phrase already exists (case-insensitive)
    existing = (
        db.query(StreamerCustomPhrase)
        .filter(
            StreamerCustomPhrase.streamer_id == streamer.id,
            StreamerCustomPhrase.phrase.ilike(payload.phrase.strip()),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="This phrase already exists")

    # Create custom phrase
    phrase_id = str(uuid.uuid4())
    custom_phrase = StreamerCustomPhrase(
        id=phrase_id,
        streamer_id=streamer.id,
        phrase=payload.phrase.strip(),
        sensitivity=payload.sensitivity,
    )

    db.add(custom_phrase)
    db.commit()
    db.refresh(custom_phrase)

    # Log without exposing phrase content
    phrase_hash = hashlib.sha256(payload.phrase.encode()).hexdigest()[:8]
    logger.info(
        f"Custom phrase added: streamer={streamer.id}, phrase_length={len(payload.phrase)}, phrase_hash={phrase_hash}"
    )

    return CustomPhraseResponse(
        id=custom_phrase.id,
        phrase=custom_phrase.phrase,
        sensitivity=custom_phrase.sensitivity,
        created_at=custom_phrase.created_at.isoformat(),
    )


@router.get("/api/irl/phrases", response_model=List[CustomPhraseResponse])
def list_custom_phrases(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    List all custom danger phrases for the current streamer.
    """
    streamer = _get_streamer(request, db)

    phrases = (
        db.query(StreamerCustomPhrase)
        .filter(StreamerCustomPhrase.streamer_id == streamer.id)
        .order_by(StreamerCustomPhrase.created_at.desc())
        .all()
    )

    return [
        CustomPhraseResponse(
            id=p.id,
            phrase=p.phrase,
            sensitivity=p.sensitivity,
            created_at=p.created_at.isoformat(),
        )
        for p in phrases
    ]


@router.delete("/api/irl/phrases/{phrase_id}")
def delete_custom_phrase(
    phrase_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Delete a custom danger phrase.
    Only the streamer who created it can delete it.
    """
    streamer = _get_streamer(request, db)

    phrase = (
        db.query(StreamerCustomPhrase)
        .filter(
            StreamerCustomPhrase.id == phrase_id,
            StreamerCustomPhrase.streamer_id == streamer.id,
        )
        .first()
    )

    if not phrase:
        raise HTTPException(status_code=404, detail="Phrase not found")

    db.delete(phrase)
    db.commit()

    logger.info(f"Custom phrase deleted: streamer={streamer.id}, phrase_id={phrase_id}")

    return {"status": "ok", "message": "Phrase deleted"}
