from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict

from backend.database.session import SessionLocal
from backend.database.models.streamer import Streamer
from backend.core.auth import get_current_user, resolve_streamer_id

router = APIRouter()


DEFAULT_SETTINGS: Dict[str, Any] = {
    "profile": {"displayName": "Kazumi Streamer", "platforms": ["Twitch"]},
    "voice": {"model": "natural", "responseSpeed": 75, "enabled": True, "triggerWord": "Kazumi"},
    "ai": {
        "personality": "helpful",
        "creativeRange": 0.7,
        "groqModel": "llama3-8b-8192",
        "useGroq": True,
        "assistantPrompt": "",
    },
    "integrations": {"obs": True, "twitch": True, "groq": True},
    "moderation": {"strictness": "medium", "autoModerate": True, "contextAware": True},
    "automation": {"autoClipping": True, "autoHighlights": True, "sceneControl": False},
    "streamerAiSuite": {
        "dynamicPrompter": {"enabled": True, "silenceSeconds": 10, "cooldownSeconds": 90},
        "crossPlatformViralEngine": {"enabled": True, "autoPost": False, "cooldownSeconds": 180, "minHypeScore": 75},
        "sentimentShield": {"enabled": True, "nuanceDetection": True, "antiHateRaid": {"enabled": True, "windowSeconds": 2, "joinThreshold": 25}},
        "contentFarm": {"enabled": True, "autoCaptionStyle": "hormozi", "verticalCropTarget": "face_plus_gameplay"},
        "streamDoctor": {"enabled": True, "droppedFramesWarn": 120, "highBitrateKbps": 6000, "micSourceName": "Mic/Aux"},
        "spoilerFilter": {"enabled": True, "action": "blur_for_streamer", "keywords": ["ending", "final boss", "phase 2", "secret ending", "twist", "spoiler", "solution", "puzzle answer"]},
        "empathyGuard": {"enabled": True, "autoWhisperResources": True},
        "audioSafeMode": {"enabled": True, "desktopAudioSource": "Desktop Audio", "copyrightThreshold": 0.8},
    },
    "superChatSorter": {
        "enabled": True,
        "extractQuestions": True,
        "blockedQuestionKeywords": [],
        "questionSourceMode": "all",
        "muteQuestionsUntil": None,
    },
    "appearance": {"darkMode": False},
}


def _merge_settings(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_settings(merged[key], value)
        else:
            merged[key] = value
    return merged


def _get_streamer(db: Session, request: Request):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return streamer


@router.get("/api/settings")
def get_settings(request: Request):
    db = SessionLocal()
    try:
        streamer = _get_streamer(db, request)
        settings = streamer.settings_json or {}
        merged = _merge_settings(DEFAULT_SETTINGS, settings)
        return merged
    finally:
        db.close()


@router.put("/streamer/settings", response_model=None)
async def update_settings(request: Request):
    # Alias route (kept for backward compatibility)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid settings payload")

    db = SessionLocal()
    try:
        streamer = _get_streamer(db, request)
        merged = _merge_settings(DEFAULT_SETTINGS, payload)
        streamer.settings_json = merged

        profile = merged.get("profile") or {}
        display_name = profile.get("displayName")
        platforms = profile.get("platforms")
        if display_name:
            streamer.display_name = display_name
        if platforms and isinstance(platforms, list):
            streamer.platform = platforms[0]

        db.commit()
        return {"status": "success", "settings": merged}
    finally:
        db.close()


@router.put("/api/settings", response_model=None)
async def update_settings_api(request: Request):
    # Alias route
    return await update_settings(request)


# ===== MOMENT DETECTION SETTINGS =====

@router.get("/api/moments/settings")
def get_moment_settings(request: Request):
    """Get moment detection settings for authenticated streamer"""
    from backend.core.settings_manager import get_settings_manager

    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")

    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.user_id == user.id).first()
        if not streamer:
            raise HTTPException(status_code=404, detail="Streamer profile not found")

        settings_manager = get_settings_manager()
        settings = settings_manager.get_settings(streamer.id)

        return {
            "status": "ok",
            "settings": settings.to_dict()
        }
    finally:
        db.close()


@router.put("/api/moments/settings")
def update_moment_settings(request: Request, body: dict):
    """Update moment detection settings"""
    from backend.core.settings_manager import get_settings_manager
    from backend.core.moment_detector import get_detector

    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")

    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.user_id == user.id).first()
        if not streamer:
            raise HTTPException(status_code=404, detail="Streamer profile not found")

        settings_manager = get_settings_manager()
        settings = settings_manager.get_settings(streamer.id)

        # Update fields from request
        if "sensitivity" in body:
            settings.sensitivity = max(0.0, min(1.0, float(body["sensitivity"])))
            # Apply to detector
            detector = get_detector()
            detector.set_sensitivity(settings.sensitivity)

        if "min_quality_score" in body:
            settings.min_quality_score = max(0.0, min(1.0, float(body["min_quality_score"])))

        if "auto_publish" in body:
            settings.auto_publish = bool(body["auto_publish"])

        if "auto_publish_platforms" in body:
            settings.auto_publish_platforms = body["auto_publish_platforms"]

        if "notify_on_clip" in body:
            settings.notify_on_clip = bool(body["notify_on_clip"])

        if "notify_on_publish" in body:
            settings.notify_on_publish = bool(body["notify_on_publish"])

        # Save to database
        settings_manager.save_settings(streamer.id, settings)

        return {
            "status": "success",
            "settings": settings.to_dict()
        }
    finally:
        db.close()
