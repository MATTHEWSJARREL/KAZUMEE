"""
Monitoring and health check endpoints.
Provides system status, metrics, and debugging information.
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import os
from pathlib import Path

from backend.core.auth import get_current_user, get_streamer_id_for_user
from backend.core.logger import get_event_log, EventType
from backend.core.clip_storage import get_clip_storage
from backend.database.session import SessionLocal
from backend.database.models.stream_event import StreamEvent
from backend.database.models.streamer import Streamer
from backend.database.models.clip import Clip

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


@router.get("/stats")
async def get_stats(current_user = Depends(get_current_user)):
    """Get system statistics and metrics"""
    streamer_id = await get_streamer_id_for_user(current_user.id)

    if not streamer_id:
        raise HTTPException(status_code=403, detail="Not a streamer")

    event_log = get_event_log()
    storage = get_clip_storage()
    storage_stats = storage.get_storage_stats()

    return {
        "clip_pipeline": event_log.get_stats(),
        "storage": storage_stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/events")
async def get_recent_events(
    current_user = Depends(get_current_user),
    limit: int = 50,
    event_type: str = None
):
    """Get recent events for debugging"""
    streamer_id = await get_streamer_id_for_user(current_user.id)

    if not streamer_id:
        raise HTTPException(status_code=403, detail="Not a streamer")

    event_log = get_event_log()
    return {
        "events": event_log.get_recent_events(limit=limit, event_type=event_type),
        "total": len(event_log.events)
    }


@router.get("/errors")
async def get_recent_errors(
    current_user = Depends(get_current_user),
    limit: int = 50
):
    """Get recent errors for debugging"""
    streamer_id = await get_streamer_id_for_user(current_user.id)

    if not streamer_id:
        raise HTTPException(status_code=403, detail="Not a streamer")

    event_log = get_event_log()
    return {
        "errors": event_log.get_errors(limit=limit),
        "total_errors": event_log.error_count
    }


@router.get("/clip-success-rate")
async def get_clip_success_rate(current_user = Depends(get_current_user)):
    """Get clip creation success rate"""
    streamer_id = await get_streamer_id_for_user(current_user.id)

    if not streamer_id:
        raise HTTPException(status_code=403, detail="Not a streamer")

    event_log = get_event_log()
    stats = event_log.get_stats()

    return {
        "success_rate": stats["success_rate"],
        "total_clips": stats["success_count"] + stats["error_count"],
        "successful": stats["success_count"],
        "failed": stats["error_count"]
    }


@router.get("/extraction-failures")
async def get_extraction_failures(
    current_user = Depends(get_current_user),
    limit: int = 20
):
    """Get recent extraction failures for debugging"""
    streamer_id = await get_streamer_id_for_user(current_user.id)

    if not streamer_id:
        raise HTTPException(status_code=403, detail="Not a streamer")

    event_log = get_event_log()
    failures = [
        e for e in event_log.events
        if e.event_type == EventType.EXTRACTION_FAILED.value
    ]

    return {
        "failures": [e.to_dict() for e in failures[-limit:]],
        "total_failures": len(failures)
    }


@router.get("/log-files")
async def get_log_files(current_user = Depends(get_current_user)):
    """Get available log files"""
    streamer_id = await get_streamer_id_for_user(current_user.id)

    if not streamer_id:
        raise HTTPException(status_code=403, detail="Not a streamer")

    log_dir = Path("backend/logs")

    if not log_dir.exists():
        return {"log_files": []}

    files = []
    for log_file in log_dir.glob("*.log"):
        size = log_file.stat().st_size
        files.append({
            "name": log_file.name,
            "size_bytes": size,
            "size_mb": round(size / 1024 / 1024, 2),
            "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
        })

    return {
        "log_files": sorted(files, key=lambda x: x["modified"], reverse=True)
    }


@router.delete("/cleanup-test-data/{streamer_username}")
async def cleanup_test_data(
    streamer_username: str,
    current_user = Depends(get_current_user)
):
    """
    DANGEROUS: Delete all stream_events and clips for a test streamer.
    Only allows cleanup of streamers with platform='test' to prevent accidents.
    Requires authentication.

    Example: DELETE /api/monitoring/cleanup-test-data/test_chat_to_detector
    """
    db = SessionLocal()
    try:
        # Find streamer
        streamer = db.query(Streamer).filter(
            Streamer.username == streamer_username
        ).first()

        if not streamer:
            raise HTTPException(status_code=404, detail="Streamer not found")

        # Only allow deletion of test streamers (safety check)
        if streamer.platform != "test":
            raise HTTPException(
                status_code=403,
                detail=f"Cleanup only allowed for test streamers. '{streamer_username}' platform={streamer.platform}"
            )

        # Delete all stream_events
        deleted_events = db.query(StreamEvent).filter(
            StreamEvent.streamer_id == streamer.id
        ).delete()

        # Delete all clips
        deleted_clips = db.query(Clip).filter(
            Clip.streamer_id == streamer.id
        ).delete()

        # Delete the streamer
        db.delete(streamer)
        db.commit()

        return {
            "success": True,
            "message": f"Deleted test streamer '{streamer_username}'",
            "deleted": {
                "streamer_id": streamer.id,
                "stream_events": deleted_events,
                "clips": deleted_clips
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
    finally:
        db.close()
