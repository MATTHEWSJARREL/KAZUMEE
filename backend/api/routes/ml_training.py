from datetime import datetime
import os

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import func

from backend.core.auth import get_current_user, resolve_streamer_id
from backend.core.taste import apply_preset, extract_tags, score_clip, update_taste_profile
from backend.database.models.clip import Clip
from backend.database.models.command import Command
from backend.database.models.ml_model_artifact import MLModelArtifact
from backend.database.models.streamer import Streamer
from backend.database.session import SessionLocal

router = APIRouter()
MODEL_NAME = "taste_profile_v1"


def _require_streamer(request: Request) -> tuple:
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    return user, streamer_id


def _ensure_artifact_table(db) -> None:
    bind = db.get_bind()
    MLModelArtifact.__table__.create(bind=bind, checkfirst=True)


def _normalize_profile_for_training(existing_profile: dict | None) -> dict:
    preset = (existing_profile or {}).get("preset") or "balanced"
    profile = apply_preset(None, preset)
    profile["tags"] = {}
    profile["approved"] = 0
    profile["rejected"] = 0
    profile["last_tags"] = []
    return profile


def _evaluate_profile(profile: dict, clips: list[Clip]) -> dict:
    sample_count = len(clips)
    if sample_count == 0:
        return {
            "sample_count": 0,
            "accuracy_pct": 0.0,
            "precision_pct": 0.0,
            "recall_pct": 0.0,
            "f1_pct": 0.0,
            "avg_confidence_pct": 0.0,
            "tp": 0,
            "tn": 0,
            "fp": 0,
            "fn": 0,
        }

    tp = tn = fp = fn = 0
    confidence_total = 0.0
    for clip in clips:
        tags = extract_tags(clip.tags)
        predicted_score = float(score_clip(profile, tags, duration_seconds=clip.duration_seconds))
        predicted_positive = predicted_score >= 0.5
        actual_positive = clip.status == "approved"
        confidence_total += min(1.0, abs(predicted_score - 0.5) * 2.0)

        if predicted_positive and actual_positive:
            tp += 1
        elif predicted_positive and not actual_positive:
            fp += 1
        elif (not predicted_positive) and actual_positive:
            fn += 1
        else:
            tn += 1

    accuracy = (tp + tn) / sample_count if sample_count else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    avg_confidence = confidence_total / sample_count if sample_count else 0.0

    return {
        "sample_count": sample_count,
        "accuracy_pct": round(accuracy * 100, 2),
        "precision_pct": round(precision * 100, 2),
        "recall_pct": round(recall * 100, 2),
        "f1_pct": round(f1 * 100, 2),
        "avg_confidence_pct": round(avg_confidence * 100, 2),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def _top_tag_features(profile: dict, limit: int = 10) -> list[dict]:
    tag_counts = profile.get("tags") or {}
    top_tags = sorted(tag_counts.items(), key=lambda x: abs(int(x[1])), reverse=True)[:limit]
    return [
        {"tag": str(tag), "weight": int(weight)}
        for tag, weight in top_tags
    ]


@router.get("/api/ml-training")
async def get_ml_training_dashboard(request: Request):
    _user, streamer_id = _require_streamer(request)
    db = SessionLocal()
    try:
        _ensure_artifact_table(db)
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        if not streamer:
            raise HTTPException(status_code=404, detail="Streamer not found")

        profile = streamer.taste_profile or {}
        approved = int(profile.get("approved") or 0)
        rejected = int(profile.get("rejected") or 0)
        total_samples = approved + rejected

        latest_artifact = (
            db.query(MLModelArtifact)
            .filter(
                MLModelArtifact.streamer_id == streamer_id,
                MLModelArtifact.model_name == MODEL_NAME,
            )
            .order_by(MLModelArtifact.model_version.desc())
            .first()
        )

        if latest_artifact and isinstance(latest_artifact.metrics, dict):
            overall_confidence = int(round(float(latest_artifact.metrics.get("accuracy_pct") or 0.0)))
        elif total_samples > 0:
            overall_confidence = int(round((approved / total_samples) * 100))
        else:
            avg_conf = (
                db.query(func.avg(Command.confidence_score))
                .filter(Command.streamer_id == streamer_id)
                .scalar()
            )
            overall_confidence = int(round(float(avg_conf or 0.0) * 100))

        tag_counts = profile.get("tags") or {}
        categories = []
        for tag, score in sorted(tag_counts.items(), key=lambda x: abs(int(x[1])), reverse=True)[:8]:
            raw = 50 + int(score) * 10
            confidence = max(0, min(100, raw))
            categories.append(
                {
                    "name": str(tag),
                    "samples": abs(int(score)),
                    "confidence": confidence,
                }
            )

        if not categories:
            categories = [{"name": "general", "samples": max(total_samples, 0), "confidence": overall_confidence}]

        artifact_history = (
            db.query(MLModelArtifact)
            .filter(
                MLModelArtifact.streamer_id == streamer_id,
                MLModelArtifact.model_name == MODEL_NAME,
            )
            .order_by(MLModelArtifact.model_version.desc())
            .limit(5)
            .all()
        )
        model_history = [
            {
                "id": item.id,
                "version": item.model_version,
                "train_samples": int(item.train_samples or 0),
                "holdout_samples": int(item.holdout_samples or 0),
                "metrics": item.metrics or {},
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in artifact_history
        ]

        recent_clips = (
            db.query(Clip)
            .filter(Clip.streamer_id == streamer_id)
            .order_by(Clip.updated_at.desc(), Clip.created_at.desc())
            .limit(20)
            .all()
        )
        recent_learning = []
        for clip in recent_clips:
            feedback_score = 0
            if clip.status == "approved":
                feedback_score = 1
            elif clip.status == "rejected":
                feedback_score = -1
            recent_learning.append(
                {
                    "id": clip.id,
                    "content": clip.title or clip.description or f"Clip #{clip.id}",
                    "category": "clip_feedback",
                    "confidence": int(round(float(clip.quality_score or 0.0) * 100)),
                    "feedbackScore": feedback_score,
                }
            )

        clips_total = (
            db.query(func.count(Clip.id))
            .filter(Clip.streamer_id == streamer_id)
            .scalar()
            or 0
        )
        auto_clips = (
            db.query(func.count(Clip.id))
            .filter(
                Clip.streamer_id == streamer_id,
                Clip.requested_by_type.in_(["ai", "ai_observer", "system", "agent"]),
            )
            .scalar()
            or 0
        )
        automation_level = int(round((auto_clips / clips_total) * 100)) if clips_total else 0
        confidence_threshold = int(round(float(os.getenv("CONFIDENCE_THRESHOLD", "0.7")) * 100))

        return {
            "overallConfidence": overall_confidence,
            "totalSamples": int(total_samples),
            "accuracyRate": overall_confidence,
            "activeModels": 1 if latest_artifact else (1 if total_samples > 0 else 0),
            "learningRate": min(100, max(0, int(total_samples))),
            "automationLevel": automation_level,
            "confidenceThreshold": confidence_threshold,
            "categories": categories,
            "recentLearning": recent_learning,
            "trainingEngine": "feedback_adaptive_v2_artifacted",
            "modelArtifact": (
                {
                    "id": latest_artifact.id,
                    "version": latest_artifact.model_version,
                    "train_samples": int(latest_artifact.train_samples or 0),
                    "holdout_samples": int(latest_artifact.holdout_samples or 0),
                    "metrics": latest_artifact.metrics or {},
                    "created_at": latest_artifact.created_at.isoformat() if latest_artifact.created_at else None,
                }
                if latest_artifact
                else None
            ),
            "modelHistory": model_history,
            "simulated": False,
        }
    finally:
        db.close()


@router.post("/api/ml-training")
async def retrain_taste_profile(request: Request):
    _user, streamer_id = _require_streamer(request)
    body = await request.json()
    action = body.get("action")
    if action != "train":
        raise HTTPException(status_code=400, detail="Invalid action")

    db = SessionLocal()
    try:
        _ensure_artifact_table(db)
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        if not streamer:
            raise HTTPException(status_code=404, detail="Streamer not found")

        reviewed_clips = (
            db.query(Clip)
            .filter(
                Clip.streamer_id == streamer_id,
                Clip.status.in_(["approved", "rejected"]),
            )
            .order_by(Clip.created_at.asc())
            .all()
        )

        total_samples = len(reviewed_clips)
        
        # Short-circuit if no reviewed clips available
        if total_samples == 0:
            return {
                "success": True,
                "message": "No reviewed clips to process. Training skipped.",
                "samplesProcessed": 0,
                "modelVersion": None,
                "metrics": None,
                "updatedAt": datetime.utcnow().isoformat(),
            }
        
        holdout_samples = max(1, int(round(total_samples * 0.2))) if total_samples >= 8 else 0
        if holdout_samples >= total_samples:
            holdout_samples = max(0, total_samples - 1)
        train_set = reviewed_clips[:-holdout_samples] if holdout_samples else reviewed_clips
        holdout_set = reviewed_clips[-holdout_samples:] if holdout_samples else []

        profile = _normalize_profile_for_training(streamer.taste_profile or {})

        for clip in train_set:
            tags = extract_tags(clip.tags)
            is_approved = clip.status == "approved"
            profile = update_taste_profile(
                profile,
                tags,
                approved=is_approved,
                duration_seconds=clip.duration_seconds,
            )

        # Refresh clip scores against the newly trained profile.
        for clip in reviewed_clips:
            tags = extract_tags(clip.tags)
            clip.quality_score = score_clip(profile, tags, duration_seconds=clip.duration_seconds)
            clip.updated_at = datetime.utcnow()

        train_metrics = _evaluate_profile(profile, train_set)
        eval_target = holdout_set if holdout_set else train_set
        eval_metrics = _evaluate_profile(profile, eval_target)

        latest_version = (
            db.query(func.max(MLModelArtifact.model_version))
            .filter(
                MLModelArtifact.streamer_id == streamer_id,
                MLModelArtifact.model_name == MODEL_NAME,
            )
            .scalar()
        )
        next_version = int(latest_version or 0) + 1

        model_state = {
            "profile": profile,
            "top_tags": _top_tag_features(profile),
        }
        metrics = {
            "evaluation_mode": "holdout_20pct" if holdout_set else "train_only_low_sample",
            "accuracy_pct": eval_metrics["accuracy_pct"],
            "precision_pct": eval_metrics["precision_pct"],
            "recall_pct": eval_metrics["recall_pct"],
            "f1_pct": eval_metrics["f1_pct"],
            "avg_confidence_pct": eval_metrics["avg_confidence_pct"],
            "train_accuracy_pct": train_metrics["accuracy_pct"],
            "train_samples": len(train_set),
            "holdout_samples": len(holdout_set),
            "tp": eval_metrics["tp"],
            "tn": eval_metrics["tn"],
            "fp": eval_metrics["fp"],
            "fn": eval_metrics["fn"],
            "generated_at": datetime.utcnow().isoformat(),
        }

        artifact = MLModelArtifact(
            streamer_id=streamer_id,
            model_name=MODEL_NAME,
            model_version=next_version,
            model_state=model_state,
            metrics=metrics,
            train_samples=len(train_set),
            holdout_samples=len(holdout_set),
        )

        streamer.taste_profile = profile
        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        return {
            "success": True,
            "message": "Learning profile rebuilt and a new model artifact was evaluated.",
            "samplesProcessed": total_samples,
            "modelVersion": artifact.model_version,
            "metrics": metrics,
            "updatedAt": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()


@router.post("/api/ml-training/feedback")
async def submit_ml_feedback(request: Request):
    _user, streamer_id = _require_streamer(request)
    body = await request.json()
    data_id = body.get("dataId")
    feedback = body.get("feedback")
    if feedback not in {"positive", "negative"}:
        raise HTTPException(status_code=400, detail="feedback must be positive or negative")

    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        if not streamer:
            raise HTTPException(status_code=404, detail="Streamer not found")

        clip = (
            db.query(Clip)
            .filter(
                Clip.id == data_id,
                Clip.streamer_id == streamer_id,
            )
            .first()
        )
        if not clip:
            raise HTTPException(status_code=404, detail="Learning data not found")

        approved = feedback == "positive"
        # Make update idempotent: only update if status changes
        previous_status = clip.status
        new_status = "approved" if approved else "rejected"
        
        if previous_status == new_status:
            # No change needed, return success
            return {"success": True, "changed": False}
        
        tags = extract_tags(clip.tags)
        streamer.taste_profile = update_taste_profile(
            streamer.taste_profile or {},
            tags,
            approved=approved,
            duration_seconds=clip.duration_seconds,
        )
        clip.quality_score = score_clip(streamer.taste_profile, tags, duration_seconds=clip.duration_seconds)
        clip.status = new_status
        clip.updated_at = datetime.utcnow()

        db.commit()
        return {"success": True, "changed": True}
    finally:
        db.close()
