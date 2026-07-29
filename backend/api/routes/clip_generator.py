"""
Clip Generator Route

Endpoint to trigger clip generation from the clip pipeline.
Can be triggered manually (via voice command "clip that" or dashboard button)
or automatically (when moment is detected).
"""

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from typing import Optional

from backend.core.auth import get_current_user
from backend.core.clip_pipeline import ClipPipeline, ClipPipelineError
from backend.database.session import get_db
from backend.database.models.clip import Clip as ClipModel
from backend.core.event_bus import get_event_bus, StreamEvent, EventType, Platform

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clips", tags=["ClipGenerator"])


class ManualClipRequest(BaseModel):
    """Manual clip trigger from voice command or dashboard button"""
    title: Optional[str] = None
    context: Optional[str] = None
    duration_seconds: int = 45


class ClipGenerationResponse(BaseModel):
    """Response after clip is generated"""
    status: str  # "success" | "queued" | "failed"
    clip_id: str
    title: Optional[str] = None
    message: Optional[str] = None
    youtube_url: Optional[str] = None


# Global clip pipeline instance
_pipeline: Optional[ClipPipeline] = None


def get_pipeline() -> ClipPipeline:
    """Get or initialize clip pipeline"""
    global _pipeline
    if _pipeline is None:
        _pipeline = ClipPipeline()
    return _pipeline


@router.post("/generate", response_model=ClipGenerationResponse)
async def generate_clip_manual(
    payload: ManualClipRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ClipGenerationResponse:
    """
    Manually trigger clip generation.

    Can be called by:
    - Voice command: "Kazumi, clip!"
    - Dashboard button: [CLIP NOW]
    - API request

    The clip generation runs in the background and returns immediately.
    """
    try:
        # For v1 testing: use hardcoded streamer_id, skip auth
        streamer_id = 1
        logger.info(f"Clip generation triggered for streamer {streamer_id}")

        # Queue clip generation to run in background
        background_tasks.add_task(
            _process_clip_generation,
            streamer_id=streamer_id,
            title=payload.title,
            context=payload.context,
            duration_seconds=payload.duration_seconds,
            db_session=db,
        )

        return ClipGenerationResponse(
            status="queued",
            clip_id=f"clip_{datetime.now().timestamp()}",
            title=payload.title or "Processing...",
            message="Clip generation queued. Check back in 1-2 minutes.",
        )

    except Exception as e:
        logger.error(f"Failed to trigger clip generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_clip_generation(
    streamer_id: int,
    title: Optional[str],
    context: Optional[str],
    duration_seconds: int,
    db_session: Session,
):
    """Background task to process clip generation"""
    try:
        pipeline = get_pipeline()
        obs_adapter = None  # Will be set from app state if needed

        # Prepare moment data
        moment_data = {
            "start_seconds": 0,  # Last 45 seconds (0-45)
            "duration_seconds": duration_seconds,
            "context": context,
            "streamer_id": streamer_id,
        }

        logger.info(f"Starting clip pipeline for streamer {streamer_id}")

        # Run the full pipeline
        result = await pipeline.process(
            moment_data=moment_data,
            obs_adapter=obs_adapter,
            streamer_id=streamer_id,
            db_session=db_session,
        )

        # Publish event to event bus
        try:
            event_bus = get_event_bus()
            if event_bus:
                event = StreamEvent(
                    event_id=result["clip_id"],
                    platform=Platform.SYSTEM,
                    event_type=EventType.CLIP_GENERATED,
                    streamer_id=streamer_id,
                    payload={
                        "title": result.get("title"),
                        "youtube_url": result.get("youtube_url"),
                        "file_path": result.get("file_path"),
                        "virality_score": result.get("virality_score", 5),
                        "status": result["status"],
                    },
                    confidence=0.95,
                )
                await event_bus.publish(event)
                logger.info(f"Published CLIP_GENERATED event: {result['clip_id']}")
        except Exception as e:
            logger.warning(f"Failed to publish clip event: {e}")

        # Store in database (v1: defer full DB integration, just log for now)
        try:
            logger.info(f"Clip ready: {result.get('file_path')} | Title: {result.get('title')} | Virality: {result.get('virality_score', 5)}")
        except Exception as e:
            logger.error(f"Failed to log clip: {e}")

        logger.info(f"✓ Clip generation complete: {result['clip_id']}")

    except Exception as e:
        logger.error(f"✗ Clip generation failed: {e}")


@router.get("/recent")
async def get_recent_clips(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Get recently generated clips for this streamer"""
    try:
        # For v1 testing: use hardcoded streamer_id
        streamer_id = 1

        clips = (
            db.query(ClipModel)
            .filter(ClipModel.streamer_id == streamer_id)
            .order_by(ClipModel.created_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "status": "success",
            "clips": [
                {
                    "id": c.id,
                    "title": c.title,
                    "youtube_url": c.youtube_url,
                    "view_count": c.view_count,
                    "created_at": c.created_at.isoformat(),
                }
                for c in clips
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get recent clips: {e}")
        raise HTTPException(status_code=500, detail=str(e))


