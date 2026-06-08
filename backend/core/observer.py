
import time
import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional

from backend.database.models.command import Command
from backend.database.models.stream_event import StreamEvent
from backend.database.models.stream_session import StreamSession
from backend.database.models.streamer import Streamer
from backend.core.event_store import insert_stream_event
from backend.core.streamer_ai_suite import streamer_ai_suite
from backend.core.health_rules import evaluate_health, filter_actions


class StreamObserver:
    def __init__(self, db_session_factory, executor=None):
        # This factory allows us to create a new DB session whenever we need to save something
        self.db_factory = db_session_factory
        self.executor = executor
        self.is_running = False

        # State Tracking
        self.last_scene = None
        self.scene_start_time = time.time()
        self.chat_velocity = 0  # msgs per minute (mocked for now)
        self.last_auto_clip_at = {}

        self.auto_clip_enabled = os.getenv("AUTO_CLIP_ENABLED", "false").lower() == "true"
        self.auto_clip_window_sec = int(os.getenv("AUTO_CLIP_WINDOW_SEC", "20"))
        self.auto_clip_min_messages = int(os.getenv("AUTO_CLIP_MIN_MESSAGES", "12"))
        self.auto_clip_cooldown_sec = int(os.getenv("AUTO_CLIP_COOLDOWN_SEC", "90"))
        self.last_suite_emit = {}

    async def start(self, obs_adapter):
        self.is_running = True
        print("?? Kazumi Observer: Active and Watching...")

        while self.is_running:
            try:
                await self.check_stream_health(obs_adapter)
            except Exception as e:
                print(f"? Observer Error: {e}")

            await asyncio.sleep(5) # Checks every 5 seconds

    async def check_stream_health(self, obs):
        streamer_id = None
        if self.db_factory:
            with self.db_factory() as db:
                streamer_id = self._get_active_streamer_id(db)

        # 1. Track scene duration without generating scene-switch suggestions.
        # The streamer-selected scene should stay active unless an explicit command
        # or safety flow changes it.
        current_scene = obs.get_current_scene()

        if current_scene != self.last_scene:
            self.last_scene = current_scene
            self.scene_start_time = time.time()

        # 2. Auto-clip based on chat velocity
        if self.auto_clip_enabled:
            await self.check_auto_clip()

        # 3. Streamer-side AI suite tick (Dynamic Prompter + Stream Doctor)
        if streamer_id:
            await self.check_streamer_ai_suite(obs, streamer_id, current_scene)

    def _get_active_streamer_id(self, db) -> Optional[int]:
        session = (
            db.query(StreamSession)
            .filter(StreamSession.status == "live")
            .order_by(StreamSession.start_time.desc())
            .first()
        )
        return session.streamer_id if session else None

    def _get_active_stream_session(self, db, streamer_id: int) -> Optional[StreamSession]:
        return (
            db.query(StreamSession)
            .filter(StreamSession.streamer_id == streamer_id, StreamSession.status == "live")
            .order_by(StreamSession.start_time.desc())
            .first()
        )

    def _suite_emit_allowed(self, streamer_id: int, event_type: str, cooldown_sec: int = 45) -> bool:
        key = (streamer_id, event_type)
        now = datetime.utcnow()
        last = self.last_suite_emit.get(key)
        if last and (now - last).total_seconds() < cooldown_sec:
            return False
        self.last_suite_emit[key] = now
        return True

    async def check_auto_clip(self):
        if not self.executor:
            return

        with self.db_factory() as db:
            streamer_id = self._get_active_streamer_id(db)
            if not streamer_id:
                return

            now = datetime.utcnow()
            last = self.last_auto_clip_at.get(streamer_id)
            if last and (now - last).total_seconds() < self.auto_clip_cooldown_sec:
                return

            window_start = now - timedelta(seconds=self.auto_clip_window_sec)
            count = (
                db.query(StreamEvent)
                .filter(
                    StreamEvent.streamer_id == streamer_id,
                    StreamEvent.event_type == "chat_message",
                    StreamEvent.created_at >= window_start,
                )
                .count()
            )

            if count >= self.auto_clip_min_messages:
                result = await self.executor.execute("save_replay_buffer", {})
                if result.status == "ok":
                    self.last_auto_clip_at[streamer_id] = now
                    await self.create_ai_suggestion(
                        intent="auto_clip",
                        reason=f"Auto-clip created after {count} chat messages in {self.auto_clip_window_sec}s.",
                        priority=85,
                        streamer_id=streamer_id,
                    )

    async def check_streamer_ai_suite(self, obs, streamer_id: int, current_scene: str):
        obs_stats = await obs.get_stats()
        if isinstance(obs_stats, dict):
            metrics = {
                "cpu": float(obs_stats.get("cpu_usage", 0) or 0),
                "mem": float(obs_stats.get("memory_usage", 0) or 0),
                "latency_ms": float(obs_stats.get("network_latency_ms", 0) or 0),
                "bitrate_kbps": float(obs_stats.get("bitrate", 0) or 0),
                "obs_connected": bool(obs_stats.get("error") is None),
                "auto_apply": os.getenv("STREAM_DOCTOR_AUTO_APPLY", "false").lower() == "true",
            }
            health_actions = filter_actions(evaluate_health(metrics), cooldown_sec=120)
            for action in health_actions:
                if action.execute and self.executor:
                    try:
                        await self.executor.execute(action.action, action.payload or {})
                    except Exception:
                        pass
                if self.db_factory:
                    with self.db_factory() as db:
                        insert_stream_event(
                            db,
                            streamer_id=streamer_id,
                            platform="kazumi_ai",
                            event_type=f"health_{action.action}",
                            username="Kazumi",
                            message=action.reason,
                            payload={
                                "severity": action.severity,
                                "confidence": action.confidence,
                                "execute": action.execute,
                                "payload": action.payload or {},
                            },
                        )
                        db.commit()

        with self.db_factory() as db:
            streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
            settings_json = streamer.settings_json if streamer else {}
            signals = streamer_ai_suite.tick(
                streamer_id=streamer_id,
                settings_json=settings_json,
                current_scene=current_scene,
                obs_stats=obs_stats if isinstance(obs_stats, dict) else {},
            )
            if not signals:
                return

            session = self._get_active_stream_session(db, streamer_id)
            if not session:
                session = StreamSession(streamer_id=streamer_id, status="live")
                db.add(session)
                db.flush()

            for idx, signal in enumerate(signals):
                event_type = signal.get("event_type", "streamer_ai_signal")
                if not self._suite_emit_allowed(streamer_id, event_type):
                    continue

                insert_stream_event(
                    db,
                    streamer_id=streamer_id,
                    platform="kazumi_ai",
                    event_type=event_type,
                    event_id=f"observer-{event_type}-{int(time.time())}-{idx}",
                    username="Kazumi",
                    message=signal.get("message"),
                    payload={
                        "feature": signal.get("feature"),
                        "severity": signal.get("severity"),
                        "title": signal.get("title"),
                        "data": signal.get("data") or {},
                        "source": "observer_tick",
                    },
                )
                db.add(
                    Command(
                        stream_session_id=session.id,
                        streamer_id=streamer_id,
                        issued_by_type="ai_observer",
                        command_text=f"AI Suggestion: {signal.get('title', 'Action')}",
                        intent=event_type,
                        ai_reasoning=signal.get("message") or "AI signal generated.",
                        status="pending",
                        priority_level=55,
                    )
                )
            db.commit()

    async def create_ai_suggestion(self, intent, reason, priority, streamer_id: Optional[int] = None):
        """Saves a suggestion to the DB for the streamer to approve"""
        print(f"?? AI SUGGESTION: {intent} | Why: {reason}")

        # If we don't have a database factory yet (like in your current main.py),
        # we just log it. Once you pass your SessionLocal, this block runs:
        if self.db_factory:
            with self.db_factory() as db:
                session_id = None
                if streamer_id:
                    active = self._get_active_stream_session(db, streamer_id)
                    if not active:
                        active = StreamSession(streamer_id=streamer_id, status="live")
                        db.add(active)
                        db.flush()
                    session_id = active.id
                if not session_id:
                    fallback = (
                        db.query(StreamSession)
                        .filter(StreamSession.status == "live")
                        .order_by(StreamSession.start_time.desc())
                        .first()
                    )
                    session_id = fallback.id if fallback else None
                if not session_id:
                    return

                new_suggestion = Command(
                    stream_session_id=session_id,
                    streamer_id=streamer_id,
                    issued_by_type="ai_observer",
                    command_text=f"AI Suggestion: {intent}",
                    intent=intent,
                    ai_reasoning=reason,
                    status="pending", # Important: Streamer must approve!
                    priority_level=priority
                )
                db.add(new_suggestion)
                db.commit()
