from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.commands.obs_adapter import obs_bridge
from backend.core.auth import get_current_user, resolve_streamer_id
from backend.core.event_store import insert_stream_event
from backend.database.session import get_db

router = APIRouter(prefix="/obs", tags=["OBS"])


class SourceToggleRequest(BaseModel):
    source_name: str
    scene_name: str | None = None


class SourceVisibilityRequest(BaseModel):
    source_name: str
    visible: bool
    scene_name: str | None = None


class SourceDeviceRequest(BaseModel):
    source_name: str
    device_id: str


def _require_streamer_id(request: Request) -> int:
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    return int(streamer_id)


@router.get("/status")
async def get_obs_status():
    status = await obs_bridge.get_status()

    # Return the keys that match what the frontend useObsTruth hook expects
    return {
        "connected": status.get("connected", False),
        "streaming": status.get("streaming", False),
        "recording": status.get("recording", False),
        "scene": status.get("current_scene", "Unknown")
    }


@router.get("/sources")
async def get_obs_sources(request: Request):
    _require_streamer_id(request)
    result = await obs_bridge.execute("get_available_sources", {})
    if result.get("status") != "ok":
        raise HTTPException(status_code=503, detail=result.get("reason", "Could not list OBS sources"))
    return result


@router.get("/cameras")
async def get_obs_cameras(request: Request):
    _require_streamer_id(request)
    result = await obs_bridge.execute("get_available_cameras", {})
    if result.get("status") != "ok":
        raise HTTPException(status_code=503, detail=result.get("reason", "Could not list camera devices"))
    return result


@router.post("/sources/toggle")
async def toggle_obs_source(payload: SourceToggleRequest, request: Request, db: Session = Depends(get_db)):
    streamer_id = _require_streamer_id(request)
    result = await obs_bridge.execute(
        "toggle_camera",
        {"source_name": payload.source_name, "scene_name": payload.scene_name},
    )
    if result.get("status") != "ok":
        raise HTTPException(status_code=400, detail=result.get("reason", "Could not toggle source"))

    insert_stream_event(
        db,
        streamer_id=streamer_id,
        platform="obs",
        event_type="obs_source_changed",
        username="Kazumi",
        message=f"{payload.source_name} toggled {'on' if result.get('visible') else 'off'}",
        payload={
            "source_name": payload.source_name,
            "visible": bool(result.get("visible")),
            "scene_name": result.get("scene_name"),
            "action": "toggle_camera",
        },
    )
    db.commit()
    return result


@router.post("/sources/visibility")
async def set_obs_source_visibility(payload: SourceVisibilityRequest, request: Request, db: Session = Depends(get_db)):
    streamer_id = _require_streamer_id(request)
    result = await obs_bridge.execute(
        "set_source_visibility",
        {"source_name": payload.source_name, "visible": payload.visible, "scene_name": payload.scene_name},
    )
    if result.get("status") != "ok":
        raise HTTPException(status_code=400, detail=result.get("reason", "Could not set source visibility"))

    insert_stream_event(
        db,
        streamer_id=streamer_id,
        platform="obs",
        event_type="obs_source_changed",
        username="Kazumi",
        message=f"{payload.source_name} set {'visible' if payload.visible else 'hidden'}",
        payload={
            "source_name": payload.source_name,
            "visible": bool(payload.visible),
            "scene_name": result.get("scene_name"),
            "action": "set_source_visibility",
        },
    )
    db.commit()
    return result


@router.post("/sources/device")
async def switch_obs_source_device(payload: SourceDeviceRequest, request: Request, db: Session = Depends(get_db)):
    streamer_id = _require_streamer_id(request)
    result = await obs_bridge.execute(
        "switch_camera_device",
        {"source_name": payload.source_name, "device_id": payload.device_id},
    )
    if result.get("status") != "ok":
        raise HTTPException(status_code=400, detail=result.get("reason", "Could not switch camera device"))

    insert_stream_event(
        db,
        streamer_id=streamer_id,
        platform="obs",
        event_type="obs_source_changed",
        username="Kazumi",
        message=f"{payload.source_name} switched camera device",
        payload={
            "source_name": payload.source_name,
            "device_id": payload.device_id,
            "action": "switch_camera_device",
        },
    )
    db.commit()
    return result


