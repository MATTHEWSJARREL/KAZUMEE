from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from datetime import datetime

from backend.database.session import get_db
from backend.database.models.clip import Clip
from backend.database.models.streamer import Streamer
from backend.core.taste import extract_tags, extract_tags_from_text, update_taste_profile, score_clip
from backend.core.export import queue_short_form_export
from backend.core.auth import get_current_user
from backend.core.event_store import insert_stream_event

router = APIRouter()


class OpenClipRequest(BaseModel):
	path: str


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


@router.post("/open")
def open_clip(req: OpenClipRequest, request: Request):
	user = get_current_user(request, required=True)
	if user.role != "streamer":
		raise HTTPException(status_code=403, detail="Streamer role required")
	# resolve and validate
	requested = os.path.abspath(req.path)
	if not requested.startswith(BASE_CLIPS_DIR):
		raise HTTPException(status_code=403, detail="Path not allowed")

	if not os.path.exists(requested):
		raise HTTPException(status_code=404, detail="File not found")

	# Only supported on Windows for now
	if os.name != "nt":
		raise HTTPException(status_code=501, detail="Open clip not supported on this OS")

	try:
		os.startfile(requested)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

	return {"status": "ok"}


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


@router.get("/pending")
def get_pending_clips(request: Request, db: Session = Depends(get_db)):
	user = get_current_user(request, required=True)
	if user.role != "streamer":
		raise HTTPException(status_code=403, detail="Streamer role required")
	"""Get all pending clips for review"""
	clips = db.query(Clip).filter(Clip.status == "pending").order_by(Clip.created_at.desc()).all()

	return {
		"clips": [
			{
				"id": clip.id,
				"title": clip.title,
				"description": clip.description,
				"file_path": clip.file_path,
				"requested_by_type": clip.requested_by_type,
				"requested_by_name": clip.requested_by_name,
				"created_at": clip.created_at.isoformat(),
				"duration_seconds": clip.duration_seconds,
				"quality_score": clip.quality_score,
				"sentiment_score": clip.sentiment_score,
				"export_status": clip.export_status,
				"export_preset": clip.export_preset,
				"export_path": clip.export_path,
				"export_updated_at": clip.export_updated_at.isoformat() if clip.export_updated_at else None,
				"notes": clip.notes
			}
			for clip in clips
		]
	}


@router.get("/recent")
def get_recent_clips(limit: int = 10, db: Session = Depends(get_db)):
	"""Get recent approved clips for dashboard"""
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


@router.post("/review")
def review_clip(req: ClipReviewRequest, request: Request, db: Session = Depends(get_db)):
	user = get_current_user(request, required=True)
	if user.role != "streamer":
		raise HTTPException(status_code=403, detail="Streamer role required")
	"""Approve, reject, or delete a clip"""
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
	elif req.action == "delete":
		clip.status = "deleted"
		clip.notes = req.notes
	else:
		raise HTTPException(status_code=400, detail="Invalid action")

	db.commit()

	return {"status": "success", "message": f"Clip {req.action}d successfully"}


@router.get("/{clip_id}")
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


@router.post("/{clip_id}/export")
def export_clip(clip_id: int, req: ClipExportRequest, request: Request, db: Session = Depends(get_db)):
	user = get_current_user(request, required=True)
	if user.role != "streamer":
		raise HTTPException(status_code=403, detail="Streamer role required")
	"""Create a short-form export job for the local agent."""
	clip = db.query(Clip).filter(Clip.id == clip_id).first()
	if not clip:
		raise HTTPException(status_code=404, detail="Clip not found")

	preset = req.preset.lower().strip()
	if preset not in ["tiktok", "shorts", "reels"]:
		raise HTTPException(status_code=400, detail="Invalid preset")

	job = queue_short_form_export(
		db,
		clip_id=clip_id,
		streamer_id=clip.streamer_id,
		input_path=clip.file_path,
		preset=preset,
		watermark_text=req.watermark_text,
		subtitles_path=req.subtitles_path,
	)
	clip.export_status = "queued"
	clip.export_preset = preset
	clip.export_path = job.get("output_path")
	clip.export_updated_at = datetime.utcnow()
	db.commit()
	return {
		"status": "success",
		"message": "Export job queued for agent.",
		"job": job,
	}
