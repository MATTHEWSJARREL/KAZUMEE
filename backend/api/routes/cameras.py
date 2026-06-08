from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import asyncio
import logging

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.database.models.streamer import Streamer
from backend.database.models.streamer_camera_source import StreamerCameraSource
from backend.database.session import get_db
from backend.commands.obs_adapter import obs_bridge

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/cameras", tags=["Cameras"])


class CameraMappingCreate(BaseModel):
    friendly_name: str
    obs_source_name: str
    obs_device_id: Optional[str] = None
    obs_input_kind: Optional[str] = None


class CameraMappingUpdate(BaseModel):
    friendly_name: Optional[str] = None
    obs_source_name: Optional[str] = None
    obs_device_id: Optional[str] = None


def _require_streamer(request: Request, db: Session):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    return db.query(Streamer).filter(Streamer.id == streamer_id).first()


@router.get("")
async def list_cameras(request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    mappings = db.query(StreamerCameraSource).filter(
        StreamerCameraSource.streamer_id == streamer.id
    ).all()

    obs_cameras = []
    try:
        result = await obs_bridge.get_available_cameras()
        obs_cameras = result.get("cameras", []) if result else []
    except asyncio.TimeoutError:
        logger.warning(f"OBS camera list timeout for streamer {streamer.id}")
        obs_cameras = []
    except Exception as e:
        logger.error(f"Failed to get available cameras: {e}")
        obs_cameras = []

    return {
        "mappings": [{"id": m.id, "friendly_name": m.friendly_name, "obs_source_name": m.obs_source_name} for m in mappings],
        "available_obs_cameras": obs_cameras,
    }


@router.post("")
def create_camera_mapping(payload: CameraMappingCreate, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    existing = db.query(StreamerCameraSource).filter(
        StreamerCameraSource.streamer_id == streamer.id,
        StreamerCameraSource.friendly_name == payload.friendly_name,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Friendly name already exists")

    mapping = StreamerCameraSource(
        streamer_id=streamer.id,
        friendly_name=payload.friendly_name,
        obs_source_name=payload.obs_source_name,
        obs_device_id=payload.obs_device_id,
        obs_input_kind=payload.obs_input_kind,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return {"status": "ok", "mapping": {"id": mapping.id, "friendly_name": mapping.friendly_name}}


@router.delete("/{mapping_id}")
def delete_camera_mapping(mapping_id: int, request: Request, db: Session = Depends(get_db)):
    streamer = _require_streamer(request, db)
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    mapping = db.query(StreamerCameraSource).filter(
        StreamerCameraSource.id == mapping_id,
        StreamerCameraSource.streamer_id == streamer.id,
    ).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    db.delete(mapping)
    db.commit()
    return {"status": "ok", "deleted": mapping_id}