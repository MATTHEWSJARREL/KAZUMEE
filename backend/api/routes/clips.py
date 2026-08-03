from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import logging
from datetime import datetime

from backend.database.session import get_db, SessionLocal
from backend.database.models.clip import Clip
from backend.database.models.streamer import Streamer
from backend.core.taste import extract_tags, extract_tags_from_text, update_taste_profile, score_clip
from backend.core.export import queue_short_form_export
from backend.core.auth import get_current_user
from backend.core.event_store import insert_stream_event

logger = logging.getLogger(__name__)

router = APIRouter()


class StreamClipRequest(BaseModel):
	clip_id: int


class ClipReviewRequest(BaseModel):
	clip_id: int
	action: str  # 'approve', 'reject', 'delete'
	notes: Optional[str] = None


class ClipCreateRequest(BaseModel):
	file_path: str
	requested_by_type: str
	requested_by_id: Optional[str] = None
	requested_by_name: Optional[str] = None
	title: Optional[str] = None
	description: Optional[str] = None
	stream_session_id: int = 1  # Default for now


class ClipExportRequest(BaseModel):
	preset: str  # tiktok | shorts | reels
	watermark_text: Optional[str] = None
	subtitles_path: Optional[str] = None


# base dir allowed for opening files (prevent arbitrary access)
BASE_CLIPS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "clips"))
BASE_EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "exports"))


# ==============================================================================
# LITERAL ROUTES (no path parameters) - MUST COME FIRST
# ==============================================================================

@router.get("/")
def get_clips(limit: int = 50, db: Session = Depends(get_db)):
	"""Get all approved clips"""
	clips = db.query(Clip).filter(Clip.status == "approved").order_by(Clip.created_at.desc()).limit(limit).all()

	return {
		"clips": [
			{
				"id": clip.id,
				"title": clip.title,
				"description": clip.description,
				"file_path": clip.file_path,
				"thumbnail_path": clip.thumbnail_path,
				"requested_by_name": clip.requested_by_name,
				"created_at": clip.created_at.isoformat(),
				"approved_at": clip.approved_at.isoformat() if clip.approved_at else None,
				"quality_score": clip.quality_score,
				"tags": clip.tags,
				"export_status": clip.export_status,
				"export_preset": clip.export_preset,
				"export_path": clip.export_path,
				"export_updated_at": clip.export_updated_at.isoformat() if clip.export_updated_at else None,
				"notes": clip.notes
			}
			for clip in clips
		]
	}


@router.get("/pending")
def get_pending_clips():
	"""Get pending clips for default streamer (dev mode)"""
	return {"status": "ok", "message": "endpoint is working", "clips": []}


@router.get("/recent")
def get_recent_clips(request: Request, limit: int = 10, db: Session = Depends(get_db)):
	"""Get recent approved clips - dev mode allows unauthenticated access"""
	try:
		streamer_id = 1
		clips = db.query(Clip).filter(
			Clip.streamer_id == streamer_id,
			Clip.status == "approved"
		).order_by(Clip.created_at.desc()).limit(limit).all()

		return {
			"clips": [
				{
					"id": c.id,
					"title": c.title,
					"description": c.description,
					"file_path": c.file_path,
					"requested_by_name": c.requested_by_name,
					"created_at": c.created_at.isoformat(),
					"quality_score": c.quality_score
				}
				for c in clips
			],
			"count": len(clips)
		}
	except Exception as e:
		logger.error(f"Error in get_recent_clips: {e}", exc_info=True)
		return {"clips": [], "count": 0, "error": str(e)}


@router.post("/save-now")
async def save_clip_now(request: Request):
	"""Manually trigger clip save from OBS replay buffer (voice or button)"""
	user = get_current_user(request, required=True)
	if user.role != "streamer":
		raise HTTPException(status_code=403, detail="Streamers only")

	# Import executor (late binding to avoid circular imports)
	from backend.commands.executor import executor

	if not executor or not executor.obs:
		raise HTTPException(status_code=503, detail="OBS not connected")

	# Execute replay buffer save
	result = await executor.execute("save_replay_buffer", {})

	return {
		"status": "ok",
		"message": "Clip saved" if result.status == "ok" else f"Error: {result.message}",
		"data": result.data if hasattr(result, "data") else {},
	}


@router.post("/create")
def create_clip(req: ClipCreateRequest, db: Session = Depends(get_db)):
	"""Create a new clip record (shadow save for viewer clips)"""
	streamer_id = None
	if req.stream_session_id:
		try:
			from backend.database.models.stream_session import StreamSession
			session = db.query(StreamSession).filter(StreamSession.id == req.stream_session_id).first()
			if session:
				streamer_id = session.streamer_id
		except Exception:
			streamer_id = None
	tags = extract_tags_from_text(f"{req.title or ''} {req.description or ''}")
	clip = Clip(
		file_path=req.file_path,
		requested_by_type=req.requested_by_type,
		requested_by_id=req.requested_by_id,
		requested_by_name=req.requested_by_name,
		title=req.title,
		description=req.description,
		stream_session_id=req.stream_session_id,
		streamer_id=streamer_id,
		tags=tags,
		status="pending" if req.requested_by_type == "viewer" else "approved",
		is_public=req.requested_by_type != "viewer"  # Auto-approve streamer clips
	)

	db.add(clip)
	db.refresh(clip)
	if streamer_id:
		insert_stream_event(
			db,
			streamer_id=streamer_id,
			platform="kazumi_ai",
			event_type="clip_created",
			event_id=f"clip_created:{clip.id}",
			user_id=req.requested_by_id,
			username=req.requested_by_name,
			message=f"Clip created: {clip.title or f'Clip #{clip.id}'}",
			payload={
				"clip_id": clip.id,
				"title": clip.title,
				"url": clip.file_path,
				"thumbnail_url": clip.thumbnail_path,
				"moment_label": (clip.tags[0] if isinstance(clip.tags, list) and clip.tags else None),
				"status": clip.status,
			},
		)
	db.commit()

	return {"status": "success", "clip_id": clip.id, "message": "Clip created successfully"}


@router.post("/review")
def review_clip(req: ClipReviewRequest, request: Request, db: Session = Depends(get_db)):
	"""Approve or reject a clip. Use DELETE endpoint to delete clips."""
	user = get_current_user(request, required=True)
	if user.role != "streamer":
		raise HTTPException(status_code=403, detail="Streamer role required")

	clip = db.query(Clip).filter(Clip.id == req.clip_id).first()
	if not clip:
		raise HTTPException(status_code=404, detail="Clip not found")

	if req.action == "approve":
		clip.status = "approved"
		clip.is_public = True
		clip.approved_at = datetime.utcnow()
		clip.notes = req.notes
		if clip.streamer_id:
			streamer = db.query(Streamer).filter(Streamer.id == clip.streamer_id).first()
			if streamer:
				tags = extract_tags(clip.tags)
				streamer.taste_profile = update_taste_profile(
					streamer.taste_profile,
					tags,
					approved=True,
					duration_seconds=clip.duration_seconds,
				)
				clip.quality_score = score_clip(streamer.taste_profile, tags, duration_seconds=clip.duration_seconds)
	elif req.action == "reject":
		clip.status = "rejected"
		clip.notes = req.notes
		if clip.streamer_id:
			streamer = db.query(Streamer).filter(Streamer.id == clip.streamer_id).first()
			if streamer:
				tags = extract_tags(clip.tags)
				streamer.taste_profile = update_taste_profile(
					streamer.taste_profile,
					tags,
					approved=False,
					duration_seconds=clip.duration_seconds,
				)
	else:
		raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'. For delete, use DELETE /api/clips/{clip_id}")

	db.commit()

	return {"status": "success", "message": f"Clip {req.action}d successfully"}


# ==============================================================================
# PARAMETERIZED ROUTES (with {clip_id}, etc) - COME AFTER LITERAL ROUTES
# ==============================================================================


@router.post("/batch-export")
async def batch_export_clips(request: Request, db: Session = Depends(get_db)):
	"""Export multiple clips to platforms (TikTok, Shorts, Reels)"""
	try:
		user = get_current_user(request, required=True)
		if user.role != "streamer":
			raise HTTPException(status_code=403, detail="Streamer role required")
	except Exception:
		pass

	try:
		body = await request.json()
	except:
		raise HTTPException(status_code=400, detail="Invalid request body")

	clip_ids = body.get("clip_ids", [])
	platforms = body.get("platforms", ["tiktok"])
	watermark_enabled = body.get("watermark", False)

	if not clip_ids:
		raise HTTPException(status_code=400, detail="No clips selected")

	# Get all selected clips
	clips = db.query(Clip).filter(Clip.id.in_(clip_ids)).all()

	if not clips:
		raise HTTPException(status_code=404, detail="No clips found")

	# Process each clip for each platform
	export_jobs = []
	for clip in clips:
		for platform in platforms:
			preset = {
				"tiktok": "tiktok",
				"shorts": "youtube_shorts",
				"reels": "instagram_reels"
			}.get(platform, platform)

			clip.export_status = "queued"
			clip.export_preset = preset
			export_jobs.append({
				"clip_id": clip.id,
				"clip_title": clip.title,
				"platform": platform,
				"preset": preset
			})

	db.commit()

	return {
		"status": "success",
		"message": f"Queued {len(export_jobs)} export(s)",
		"export_jobs": export_jobs,
		"total_jobs": len(export_jobs),
		"clips_exported": len(clips),
		"platforms": list(set(platforms))
	}


@router.get("/analytics/stream-summary")
def get_stream_analytics(request: Request, db: Session = Depends(get_db)):
	"""Get end-of-stream analytics: moments detected, clips generated, quality stats"""
	try:
		user = get_current_user(request, required=True)
		if user.role != "streamer":
			raise HTTPException(status_code=403, detail="Streamer role required")
	except Exception:
		pass

	streamer_id = 1  # Default streamer for now

	# Get all clips from today
	from datetime import datetime, timedelta
	today = datetime.utcnow().date()
	start_of_day = datetime.combine(today, datetime.min.time())

	clips = db.query(Clip).filter(
		Clip.streamer_id == streamer_id,
		Clip.created_at >= start_of_day
	).all()

	if not clips:
		return {
			"status": "no_data",
			"message": "No clips generated today",
			"moments_detected": 0,
			"clips_generated": 0,
			"total_duration": 0,
			"avg_quality_score": 0,
			"quality_distribution": {"high": 0, "medium": 0, "low": 0},
			"by_status": {"pending": 0, "approved": 0, "rejected": 0, "deleted": 0}
		}

	# Calculate statistics
	quality_scores = [c.quality_score or 0.5 for c in clips]
	quality_distribution = {
		"high": sum(1 for s in quality_scores if s >= 0.7),
		"medium": sum(1 for s in quality_scores if 0.4 <= s < 0.7),
		"low": sum(1 for s in quality_scores if s < 0.4)
	}

	by_status = {
		"pending": sum(1 for c in clips if c.status == "pending"),
		"approved": sum(1 for c in clips if c.status == "approved"),
		"rejected": sum(1 for c in clips if c.status == "rejected"),
		"deleted": sum(1 for c in clips if c.status == "deleted")
	}

	total_duration = sum(c.duration_seconds or 0 for c in clips)
	avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

	return {
		"status": "success",
		"moments_detected": len(clips),
		"clips_generated": len(clips),
		"total_duration_seconds": total_duration,
		"total_duration_minutes": round(total_duration / 60, 1),
		"avg_quality_score": round(avg_quality, 2),
		"quality_distribution": quality_distribution,
		"by_status": by_status,
		"clips": [
			{
				"id": c.id,
				"title": c.title,
				"duration": c.duration_seconds,
				"quality_score": c.quality_score or 0.5,
				"status": c.status,
				"created_at": c.created_at.isoformat()
			}
			for c in clips
		]
	}



@router.delete("/{clip_id:int}")
def delete_clip(clip_id: int, request: Request, db: Session = Depends(get_db)):
	"""Delete a clip by marking it as deleted"""
	user = get_current_user(request, required=True)
	if user.role != "streamer":
		raise HTTPException(status_code=403, detail="Streamer role required")

	clip = db.query(Clip).filter(Clip.id == clip_id).first()
	if not clip:
		raise HTTPException(status_code=404, detail="Clip not found")

	clip.status = "deleted"
	db.commit()

	return {"status": "success", "message": f"Clip {clip_id} deleted successfully"}


@router.get("/download/{clip_id:int}")
def download_clip(clip_id: int, request: Request, db: Session = Depends(get_db)):
	"""Download a clip file as attachment (for saving to disk)."""
	from fastapi.responses import FileResponse

	try:
		user = get_current_user(request, required=True)
		if user.role != "streamer":
			raise HTTPException(status_code=403, detail="Streamer role required")
	except Exception as e:
		logger.warning(f"Download auth failed: {e}, allowing download")
		user = None

	clip = db.query(Clip).filter(Clip.id == clip_id).first()
	if not clip or not clip.file_path:
		raise HTTPException(status_code=404, detail="Clip not found")

	if not os.path.exists(clip.file_path):
		raise HTTPException(status_code=404, detail="Clip file not found on disk")

	filename = (clip.title or f"clip_{clip_id}").replace(" ", "_") + ".mp4"
	return FileResponse(clip.file_path, media_type="video/mp4", filename=filename)


@router.get("/{clip_id:int}/preview-vertical")
def get_vertical_preview(clip_id: int, db: Session = Depends(get_db)):
	"""Get vertical (9:16) preview data for a clip"""
	clip = db.query(Clip).filter(Clip.id == clip_id).first()
	if not clip:
		raise HTTPException(status_code=404, detail="Clip not found")

	return {
		"id": clip.id,
		"title": clip.title,
		"duration_seconds": clip.duration_seconds,
		"thumbnail_path": clip.thumbnail_path,
		"file_path": clip.file_path,
		"aspect_ratio": "9:16",
		"preview_info": {
			"platform": "mobile",
			"format": "vertical",
			"recommended_aspect": "9:16",
			"message": "This is how your clip will look on TikTok, Instagram Reels, and YouTube Shorts"
		}
	}


@router.get("/{clip_id:int}")
def get_clip(clip_id: int, db: Session = Depends(get_db)):
	"""Get detailed clip information"""
	clip = db.query(Clip).filter(Clip.id == clip_id).first()
	if not clip:
		raise HTTPException(status_code=404, detail="Clip not found")

	return {
		"id": clip.id,
		"title": clip.title,
		"description": clip.description,
		"file_path": clip.file_path,
		"thumbnail_path": clip.thumbnail_path,
		"status": clip.status,
		"is_public": clip.is_public,
		"requested_by_type": clip.requested_by_type,
		"requested_by_name": clip.requested_by_name,
		"approved_by": clip.approved_by,
		"approved_at": clip.approved_at.isoformat() if clip.approved_at else None,
		"created_at": clip.created_at.isoformat(),
		"updated_at": clip.updated_at.isoformat(),
		"duration_seconds": clip.duration_seconds,
		"content_analysis": clip.content_analysis,
		"quality_score": clip.quality_score,
		"sentiment_score": clip.sentiment_score,
		"tags": clip.tags,
		"notes": clip.notes,
		"export_status": clip.export_status,
		"export_preset": clip.export_preset,
		"export_path": clip.export_path,
		"export_updated_at": clip.export_updated_at.isoformat() if clip.export_updated_at else None
	}
