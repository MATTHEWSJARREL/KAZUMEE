from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import func

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.database.session import SessionLocal
from backend.database.models.viewer_action import ViewerAction
from backend.database.models.viewer import Viewer
from backend.database.models.clip import Clip
from backend.database.models.command import Command
from backend.database.models.stream_event import StreamEvent

router = APIRouter()


@router.get("/overview")
async def analytics_overview(request: Request, hours: int = 24):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    lookback_hours = max(1, min(hours, 168))
    since = datetime.utcnow() - timedelta(hours=lookback_hours)

    db = SessionLocal()
    try:
        events_total = (
            db.query(func.count(StreamEvent.id))
            .filter(StreamEvent.streamer_id == streamer_id, StreamEvent.created_at >= since)
            .scalar()
            or 0
        )
        commands_total = (
            db.query(func.count(Command.id))
            .filter(Command.streamer_id == streamer_id, Command.created_at >= since)
            .scalar()
            or 0
        )
        pending_commands = (
            db.query(func.count(Command.id))
            .filter(
                Command.streamer_id == streamer_id,
                Command.created_at >= since,
                Command.status == "pending",
            )
            .scalar()
            or 0
        )
        clips_total = (
            db.query(func.count(Clip.id))
            .filter(Clip.streamer_id == streamer_id, Clip.created_at >= since)
            .scalar()
            or 0
        )
        approved_clips = (
            db.query(func.count(Clip.id))
            .filter(
                Clip.streamer_id == streamer_id,
                Clip.created_at >= since,
                Clip.status == "approved",
            )
            .scalar()
            or 0
        )
        viewer_actions_total = (
            db.query(func.count(ViewerAction.id))
            .filter(ViewerAction.streamer_id == streamer_id, ViewerAction.created_at >= since)
            .scalar()
            or 0
        )
        total_credits_spent = (
            db.query(func.coalesce(func.sum(ViewerAction.cost), 0))
            .filter(ViewerAction.streamer_id == streamer_id, ViewerAction.created_at >= since)
            .scalar()
            or 0
        )

        return {
            "status": "success",
            "window_hours": lookback_hours,
            "metrics": {
                "events_total": int(events_total),
                "commands_total": int(commands_total),
                "commands_pending": int(pending_commands),
                "clips_total": int(clips_total),
                "clips_approved": int(approved_clips),
                "viewer_actions_total": int(viewer_actions_total),
                "total_credits_spent": int(total_credits_spent),
            },
        }
    finally:
        db.close()


@router.get("/monetization")
async def monetization_metrics(request: Request, days: int = 30):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    lookback_days = max(1, min(days, 180))
    since = datetime.utcnow() - timedelta(days=lookback_days)

    db = SessionLocal()
    try:
        action_query = db.query(ViewerAction).filter(
            ViewerAction.streamer_id == streamer_id,
            ViewerAction.created_at >= since,
        )
        actions = action_query.all()
        total_actions = len(actions)
        total_spend = sum(a.cost or 0 for a in actions)
        action_counter = Counter(a.action_type for a in actions)

        unique_viewers = len({a.viewer_id for a in actions if a.viewer_id is not None})

        viewer_count = (
            db.query(func.count(Viewer.id))
            .filter(Viewer.active_streamer_id == streamer_id)
            .scalar()
            or 0
        )

        export_actions = [a for a in actions if a.action_type == "export_clip"]
        executed = [a for a in actions if a.status == "executed"]
        export_success = [a for a in export_actions if a.status in {"queued", "executed"}]

        approved_clips = (
            db.query(func.count(Clip.id))
            .filter(Clip.streamer_id == streamer_id, Clip.status == "approved", Clip.created_at >= since)
            .scalar()
            or 0
        )

        conversion_rate = (unique_viewers / viewer_count) * 100 if viewer_count else 0.0
        execution_rate = (len(executed) / total_actions) * 100 if total_actions else 0.0
        export_rate = (len(export_success) / max(len(export_actions), 1)) * 100 if export_actions else 0.0

        recommendations = []
        if conversion_rate < 8:
            recommendations.append("Low participation: add a visible viewer CTA for voting/redeems every 20-30 minutes.")
        if export_actions and export_rate < 60:
            recommendations.append("Export completion is weak: tighten queue processing and show export ETA in UI.")
        if action_counter.get("vote_scene", 0) < 10:
            recommendations.append("Scene voting volume is low: promote vote prompts during transitions.")
        if not recommendations:
            recommendations.append("Engagement loop is healthy. Focus on scaling clip-to-share workflows.")

        return {
            "status": "success",
            "window_days": lookback_days,
            "metrics": {
                "active_viewers": viewer_count,
                "engaged_viewers": unique_viewers,
                "engagement_conversion_rate": round(conversion_rate, 1),
                "total_actions": total_actions,
                "total_credits_spent": total_spend,
                "action_execution_rate": round(execution_rate, 1),
                "export_completion_rate": round(export_rate, 1),
                "approved_clips": int(approved_clips),
                "top_actions": dict(action_counter.most_common(5)),
            },
            "recommendations": recommendations,
        }
    finally:
        db.close()
