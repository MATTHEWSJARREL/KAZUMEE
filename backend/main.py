from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
from contextlib import asynccontextmanager
import os
import secrets
from datetime import datetime
from datetime import timedelta
from groq import Groq, AsyncGroq
from sqlalchemy import text, func
from typing import Optional, List, Dict, Any
from collections import defaultdict, deque
import time
import cachetools
import threading
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import routers - v1 core only
from backend.api.routes import (
    auth,
    clips,
    commands,
    obs as obs_router,
    streams,
)

from backend.api.routes import moment_finder as moment_finder_router
from backend.api.routes import moment_detection as moment_detection_router
from backend.api.routes import settings as settings_router
from backend.api.routes import post_stream_report as post_stream_report_router
from backend.api.routes import groq_proxy as groq_proxy_router
# Removed: companion router (v1.1+ feature, not needed for v1)
from backend.api.routes import clip_generator as clip_generator_router


# Central dependencies
from backend.commands.obs_adapter import obs_bridge
from backend.researcher.clip_searcher_simple import VectorClipService as ClipSearcher
from backend.core.logger import get_logger
from backend.api.websockets import manager as ws_manager
from backend.commands.executor import CommandExecutor
from backend.commands.service import CommandService
from backend.brain.decider import brain_decider
from backend.brain.schemas import BrainAction
from backend.core.observer import StreamObserver
from backend.database.session import SessionLocal
from backend.database.models.command import Command as CommandModel
from backend.database.models.streamer import Streamer as StreamerModel
from backend.database.models.stream_session import StreamSession as StreamSessionModel
from backend.database.models.viewer import Viewer as ViewerModel
from backend.database.models.viewer_action import ViewerAction
from backend.core.auth import (
    get_user_by_id,
    get_current_user,
    get_user_from_token,
    get_streamer_id_for_user,
    verify_stream_access_token,
    resolve_streamer_id,
)
from backend.core.ingestion import ingestion_loop
from backend.core.search import search_links, format_links_for_chat
from backend.core.policy import evaluate_action
from backend.core.pricing import limit_violation
# Removed: voice_agent (v1.1+ feature, requires speech_recognition library)
from backend.core.rate_limiter import limiter
from backend.core.event_bus import init_event_bus, get_event_bus

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

import re

# Initialize AsyncGroq client (lazy-load to avoid startup failure)
_groq_client = None
def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            try:
                _groq_client = AsyncGroq(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Groq: {e}")
    return _groq_client

# Keep old name for backward compatibility
client = None  # Will be None if key not set, use get_groq_client() instead

# Global In-Memory Event Log (The "Chat History")
event_log = [
    {
        "type": "ai_decision",
        "description": "System Online",
        "commentary": "Kazumi Core initialized. Waiting for input...",
        "time": datetime.now().strftime("%H:%M"),
        "status": "completed"
    }
]

# In-memory command queue for the Command Center UI
command_queue: List[Dict[str, Any]] = []
command_queue_next_id = 1

OBS_CONFIRMATION_ACTIONS = {
    "switch_scene",
    "mute_mic",
    "unmute_mic",
    "set_audio_level",
    "reduce_bitrate",
    "start_recording",
    "stop_recording",
    "start_streaming",
    "stop_streaming",
    "toggle_camera",
    "switch_camera_device",
    "set_source_visibility",
    "panic_mode",
    "save_replay_buffer",
}

# In-memory settings store
settings_store = {
    "profile": {"displayName": "Kazumi Streamer", "platforms": ["Twitch"]},
    "voice": {"model": "natural", "responseSpeed": 75, "enabled": True, "triggerWord": "Kazumi"},
    "ai": {"personality": "helpful", "creativeRange": 0.7, "groqModel": "llama3-8b-8192"},
    "integrations": {"obs": True, "twitch": True, "groq": True},
    "moderation": {"strictness": "medium", "autoModerate": True, "contextAware": True},
    "automation": {"autoClipping": True, "autoHighlights": True, "sceneControl": False},
    "streamerAiSuite": {
        "dynamicPrompter": {"enabled": True, "silenceSeconds": 10, "cooldownSeconds": 90},
        "crossPlatformViralEngine": {"enabled": True, "autoPost": False, "cooldownSeconds": 180, "minHypeScore": 75},
        "sentimentShield": {"enabled": True, "nuanceDetection": True, "antiHateRaid": {"enabled": True, "windowSeconds": 2, "joinThreshold": 25}},
        "contentFarm": {"enabled": True, "autoCaptionStyle": "hormozi", "verticalCropTarget": "face_plus_gameplay"},
        "streamDoctor": {"enabled": True, "droppedFramesWarn": 120, "highBitrateKbps": 6000, "micSourceName": "Mic/Aux"},
        "spoilerFilter": {"enabled": True, "action": "blur_for_streamer"},
        "empathyGuard": {"enabled": True, "autoWhisperResources": True},
        "audioSafeMode": {"enabled": True, "desktopAudioSource": "Desktop Audio", "copyrightThreshold": 0.8},
    },
    "appearance": {"darkMode": False},
}


def _ensure_runtime_schema_compatibility():
    """Best-effort schema patching for partially migrated local databases."""
    db = SessionLocal()
    log = get_logger("SchemaCompat")
    statements = [
        "ALTER TABLE streamers ADD COLUMN IF NOT EXISTS user_id integer",
        "ALTER TABLE streamers ADD COLUMN IF NOT EXISTS operation_mode varchar(32) DEFAULT 'hybrid'",
        "ALTER TABLE streamers ADD COLUMN IF NOT EXISTS auto_approve_min_tier varchar(32) DEFAULT 'vip'",
        "ALTER TABLE streamers ADD COLUMN IF NOT EXISTS policy_json json",
        "ALTER TABLE streamers ADD COLUMN IF NOT EXISTS taste_profile json",
        "ALTER TABLE streamers ADD COLUMN IF NOT EXISTS settings_json json",
        "ALTER TABLE streamers ADD COLUMN IF NOT EXISTS subscription_tier varchar(32) DEFAULT 'free'",
        "ALTER TABLE streamers ADD COLUMN IF NOT EXISTS subscription_status varchar(32) DEFAULT 'inactive'",
        "ALTER TABLE streamers ADD COLUMN IF NOT EXISTS subscription_will_cancel boolean DEFAULT false",
        "ALTER TABLE viewers ADD COLUMN IF NOT EXISTS user_id integer",
        "ALTER TABLE viewers ADD COLUMN IF NOT EXISTS active_streamer_id integer",
        "ALTER TABLE viewers ADD COLUMN IF NOT EXISTS platform_user_id varchar",
        "ALTER TABLE viewers ADD COLUMN IF NOT EXISTS is_subscriber boolean DEFAULT false",
        "ALTER TABLE viewers ADD COLUMN IF NOT EXISTS tier varchar(32) DEFAULT 'free'",
        "ALTER TABLE viewers ADD COLUMN IF NOT EXISTS credits integer DEFAULT 100",
        "ALTER TABLE viewers ADD COLUMN IF NOT EXISTS total_spent integer DEFAULT 0",
        "ALTER TABLE viewers ADD COLUMN IF NOT EXISTS preferences_json json",
        "ALTER TABLE commands ADD COLUMN IF NOT EXISTS streamer_id integer",
        "ALTER TABLE commands ADD COLUMN IF NOT EXISTS ai_reasoning varchar",
        "ALTER TABLE commands ADD COLUMN IF NOT EXISTS confidence_score double precision DEFAULT 1.0",
        "ALTER TABLE commands ADD COLUMN IF NOT EXISTS credit_cost integer DEFAULT 0",
        "ALTER TABLE stream_events ADD COLUMN IF NOT EXISTS event_id varchar",
        "CREATE INDEX IF NOT EXISTS ix_commands_streamer_id ON commands (streamer_id)",
        "CREATE INDEX IF NOT EXISTS ix_viewers_user_id ON viewers (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_viewers_active_streamer_id ON viewers (active_streamer_id)",
        "CREATE INDEX IF NOT EXISTS ix_stream_events_event_id ON stream_events (event_id)",
    ]
    failed = 0
    try:
        for stmt in statements:
            try:
                db.execute(text(stmt))
                db.commit()
            except Exception as exc:
                failed += 1
                db.rollback()
                log.warning("Schema compatibility statement failed: %s | %s", stmt, exc)
        if failed:
            log.warning("Schema compatibility applied with %s failed statements", failed)
    finally:
        db.close()

# Queue helpers
def _get_or_create_streamer(db) -> StreamerModel:
    streamer = db.query(StreamerModel).first()
    if streamer:
        return streamer
    streamer = StreamerModel(username="kazumi", display_name="Kazumi Streamer", platform="local")
    db.add(streamer)
    db.commit()
    db.refresh(streamer)
    return streamer

def _get_or_create_stream_session(db, streamer_id: Optional[int] = None) -> StreamSessionModel:
    query = db.query(StreamSessionModel).filter(StreamSessionModel.status == "live")
    if streamer_id:
        query = query.filter(StreamSessionModel.streamer_id == streamer_id)
    session = query.order_by(StreamSessionModel.start_time.desc()).first()
    if session:
        return session
    if streamer_id:
        session = StreamSessionModel(streamer_id=streamer_id, status="live")
    else:
        streamer = _get_or_create_streamer(db)
        session = StreamSessionModel(streamer_id=streamer.id, status="live")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def _serialize_command(cmd: CommandModel) -> Dict[str, Any]:
    priority = cmd.priority_level or 0
    if priority >= 50:
        tier = "vip"
    elif priority >= 20:
        tier = "premium"
    else:
        tier = "free"
    return {
        "id": cmd.id,
        "priority": priority,
        "command_text": cmd.command_text,
        "viewer_username": cmd.issued_by_id or "viewer",
        "viewer_tier": tier,
        "command_type": cmd.issued_by_type or "viewer",
        "status": cmd.status or "pending",
        "intent": cmd.intent,
        "ai_reasoning": cmd.ai_reasoning,
        "confidence_score": cmd.confidence_score,
        "created_at": cmd.created_at.isoformat() if cmd.created_at else None,
    }

def _get_streamer_id_for_user(user) -> Optional[int]:
    if not user or user.role != "streamer":
        return None
    db = SessionLocal()
    try:
        streamer = db.query(StreamerModel).filter(StreamerModel.user_id == user.id).first()
        return streamer.id if streamer else None
    finally:
        db.close()

def _enqueue_command(
    command_text: str,
    viewer_username: str = "viewer",
    viewer_tier: str = "free",
    streamer_id: Optional[int] = None,
    intent: str = "viewer_request",
    ai_reasoning: Optional[str] = None,
    confidence_score: float = 1.0,
) -> Dict[str, Any]:
    try:
        db = SessionLocal()
        try:
            session = _get_or_create_stream_session(db, streamer_id=streamer_id)
            priority = 50 if viewer_tier == "vip" else 10
            cmd = CommandModel(
                stream_session_id=session.id,
                streamer_id=session.streamer_id,
                issued_by_type="viewer",
                issued_by_id=viewer_username,
                command_text=command_text,
                intent=intent,
                ai_reasoning=ai_reasoning,
                confidence_score=confidence_score,
                status="pending",
                priority_level=priority,
            )
            db.add(cmd)
            db.commit()
            db.refresh(cmd)
            return _serialize_command(cmd)
        finally:
            db.close()
    except Exception:
        global command_queue_next_id
        item = {
            "id": command_queue_next_id,
            "priority": 50 if viewer_tier == "vip" else 10,
            "command_text": command_text,
            "viewer_username": viewer_username,
            "viewer_tier": viewer_tier,
            "command_type": "viewer",
            "status": "pending",
            "intent": intent,
            "ai_reasoning": ai_reasoning,
            "confidence_score": confidence_score,
            "created_at": datetime.utcnow().isoformat(),
        }
        command_queue_next_id += 1
        command_queue.insert(0, item)
        return item

def _find_queue_item(command_id: int) -> Optional[Dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            cmd = db.query(CommandModel).filter(CommandModel.id == command_id).first()
            return _serialize_command(cmd) if cmd else None
        finally:
            db.close()
    except Exception:
        for item in command_queue:
            if item["id"] == command_id:
                return item
        return None

# Global clip cooldown for viewers
last_clip_time = None

# 1. Define what the incoming data looks like
class CommandRequest(BaseModel):
    command: str
    role: str  # 'streamer' or 'viewer'

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    print("Kazumi is waking up...")

    # Initialize Event Bus (Redis Streams + PostgreSQL)
    try:
        event_bus = await init_event_bus()
        app.state.event_bus = event_bus
        print("[OK] Event Bus initialized (Redis Streams + PostgreSQL)")
    except Exception as e:
        print(f"[WARN] Event Bus failed to initialize: {e}")
        print("  Continuing without event bus (in-memory only)")
        app.state.event_bus = None

    _ensure_runtime_schema_compatibility()

    # Initialize other services first
    clip_searcher = ClipSearcher(base_dir=r"backend/data/clips")
    log = get_logger("Broadcaster")

    def broadcaster(event: dict):
        try:
            log.info("BROADCAST: %s", event)
        except Exception:
            print("BROADCAST:", event)

        try:
            # We wrap the broadcast in a task so it doesn't block
            asyncio.create_task(ws_manager.broadcast(event))
        except Exception:
            log.exception("Failed to broadcast websocket event")

    obs_instance = obs_bridge
    app.state.obs_adapter = obs_instance

    if os.getenv("AUTO_CLIP_ENABLED", "false").lower() == "true":
        try:
            await obs_instance.start_replay_buffer()
        except Exception:
            pass

    executor = CommandExecutor(
        obs=obs_instance,
        clip_searcher=clip_searcher,
        broadcaster=broadcaster,
        db_session_factory=SessionLocal,
    )

    app.state.executor = executor

    observer = StreamObserver(db_session_factory=SessionLocal, executor=executor)
    app.state.observer = observer
    asyncio.create_task(observer.start(obs_adapter=obs_instance))

    command_service = CommandService(executor)
    commands.init_command_service(command_service)
    app.state.command_service = command_service

    async def _voice_agent_command_callback(command_text: str, transcript: str, cfg: dict):
        """
        Backend always-on voice callback:
        - optional AI routing
        - executes OBS intents
        - emits websocket event for UI visibility
        """
        streamer_id = int(cfg.get("streamer_id") or 0)
        use_ai = bool(cfg.get("use_ai", True))

        action = None
        message = ""
        status = "no_action"

        try:
            if use_ai:
                ai_result = await command_service._process_with_ai(command_text, is_event=False)
                action = ai_result.get("action") if isinstance(ai_result, dict) else None
                message = (ai_result.get("commentary") if isinstance(ai_result, dict) else "") or ""

                exec_result = ai_result.get("result") if isinstance(ai_result, dict) else None
                exec_status = None
                exec_message = None
                if exec_result is not None:
                    if isinstance(exec_result, dict):
                        exec_status = exec_result.get("status")
                        exec_message = exec_result.get("message")
                    else:
                        exec_status = getattr(exec_result, "status", None)
                        exec_message = getattr(exec_result, "message", None)
                if exec_status == "ok":
                    status = "executed"
                elif action:
                    status = "error"
                else:
                    status = "no_action"
                if exec_message:
                    message = exec_message
            else:
                scenes = await obs_instance.get_all_scene_names()
                decision = brain_decider.decide(command_text, scenes)
                if decision.decision == "execute" and decision.action:
                    action = decision.action.value
                    result = await executor.execute(action, decision.payload or {})
                    status = "executed" if result.status == "ok" else "error"
                    message = result.message
                else:
                    status = "no_action"
                    message = decision.reason or "Command not recognized"

            voice_event = {
                "type": "voice_agent_event",
                "streamer_id": streamer_id,
                "data": {
                    "command": command_text,
                    "transcript": transcript,
                    "action": action,
                    "status": status,
                    "message": message,
                    "source": "voice_agent",
                },
            }
            # Special hook used by VoiceAgentService for instant streamer feedback.
            if command_text == "__notify_clipping__":
                asyncio.create_task(
                    ws_manager.broadcast(
                        {
                            "type": "toast",
                            "streamer_id": streamer_id,
                            "data": {"message": "Zumi is clipping that now..."},
                        }
                    )
                )
                return {"status": "ok", "action": None, "message": "notified"}

            asyncio.create_task(ws_manager.broadcast(voice_event))

            event_log.insert(
                0,
                {
                    "type": "voice_agent",
                    "description": transcript,
                    "commentary": message or f"Processed voice command: {command_text}",
                    "time": datetime.now().strftime("%H:%M"),
                    "status": "completed" if status == "executed" else status,
                },
            )
            if len(event_log) > 100:
                event_log.pop()

            return {
                "status": status,
                "action": action,
                "message": message,
            }
        except Exception as exc:
            failure = {
                "status": "error",
                "action": action,
                "message": f"Voice callback failed: {exc}",
            }
            asyncio.create_task(
                ws_manager.broadcast(
                    {
                        "type": "voice_agent_event",
                        "streamer_id": streamer_id,
                        "data": {
                            "command": command_text,
                            "transcript": transcript,
                            "action": action,
                            "status": "error",
                            "message": str(exc),
                            "source": "voice_agent",
                        },
                    }
                )
            )
            return failure

    # Disabled for V1 MVP: app.state.voice_agent = VoiceAgentService(...)

    # Initialize streamer mode (defaults to True for security)
    app.state.streamer_mode = True

    # Start ingestion loop
    stop_event = asyncio.Event()
    app.state.ingestion_stop = stop_event
    app.state.ingestion_task = asyncio.create_task(ingestion_loop(stop_event))

    # Initialize Clip Generator Service (uses OBS adapter for real clip extraction)
    try:
        from backend.core.clip_generator_service import ClipGeneratorService, set_clip_generator
        from backend.core.moment_detector import get_detector

        clip_generator = ClipGeneratorService(obs_adapter=obs_instance)
        set_clip_generator(clip_generator)
        app.state.clip_generator = clip_generator
        print("[OK] Clip Generator Service initialized")

        # Wire detector to clip generator callback
        detector = get_detector()
        detector.on_moment_detected(clip_generator.on_moment_detected)
        print("[OK] Detector wired to Clip Generator Service")
    except Exception as e:
        print(f"[WARN] Clip Generator Service failed: {e}")
        app.state.clip_generator = None

    # Initialize OBS Audio Poller (polls OBS audio levels for moment detection)
    try:
        from backend.core.obs_audio_poller import OBSAudioPoller, set_audio_poller

        detector = get_detector()
        audio_poller = OBSAudioPoller(
            obs_adapter=obs_instance,
            detector=detector,
            poll_interval_ms=500  # Poll every 500ms
        )
        set_audio_poller(audio_poller)
        await audio_poller.start()
        app.state.audio_poller = audio_poller
        print("[OK] OBS Audio Poller started")
    except Exception as e:
        print(f"[WARN] OBS Audio Poller failed: {e}")
        app.state.audio_poller = None

    yield  # This is where the app actually runs

    # --- SHUTDOWN LOGIC ---
    print("Kazumi is going to sleep...")

    # Stop OBS Audio Poller
    if hasattr(app.state, "audio_poller") and app.state.audio_poller:
        try:
            await app.state.audio_poller.stop()
            print("[OK] OBS Audio Poller stopped")
        except Exception as e:
            print(f"[WARN] Audio Poller shutdown error: {e}")

    # Close Event Bus
    if hasattr(app.state, "event_bus") and app.state.event_bus:
        await app.state.event_bus.close()
        print("[OK] Event Bus closed")

    if hasattr(app.state, "observer"):
        app.state.observer.is_running = False
    if hasattr(app.state, "ingestion_stop"):
        app.state.ingestion_stop.set()
    if hasattr(app.state, "ingestion_task"):
        try:
            await app.state.ingestion_task
        except Exception:
            pass

# --------------------------------------------------
# CREATE APP
# --------------------------------------------------
app = FastAPI(title="Kazumi Backend API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_RATE_WINDOW_SECONDS = 60
# Use TTLCache with maxsize limit and TTL expiration
_RATE_BUCKETS: cachetools.TTLCache = cachetools.TTLCache(maxsize=10000, ttl=_RATE_WINDOW_SECONDS)
# Thread-safe lock for rate bucket access
_RATE_BUCKETS_LOCK = threading.RLock()

# Track recently evicted keys to detect when buckets are recreated
_EVICTED_KEYS = set()


def _on_rate_bucket_evicted(key):
    """Callback when a rate bucket is evicted from the cache due to TTL or LRU.
    
    Logs the eviction and tracks the key so we can warn if it's recreated.
    """
    get_logger("RateLimiter").info(f"Rate bucket evicted (TTL or LRU): {key}")
    with _RATE_BUCKETS_LOCK:
        _EVICTED_KEYS.add(key)


def _resolve_route_limit(path: str) -> int | None:
    # Dev/test endpoints - no rate limit
    if path in {"/api/moments/test", "/api/moments/chat-event", "/api/moments/audio-event", "/api/moments/reset"}:
        return None
    if path.startswith("/api/ingest"):
        return 120
    if path.startswith("/auth"):
        return 10
    if path in {
        "/api/viewer/catchup/recap",
        "/api/viewer/companion/analyze",
        "/api/viewer/companion/retry-suggestion",
        "/api/streamer/director/backseat",
    }:
        return 30
    if any(
        path.startswith(prefix)
        for prefix in (
            "/api",
            "/auth",
            "/commands",
            "/integrations",
            "/moderation",
            "/streams",
            "/policy",
            "/agent",
            "/obs",
            "/analytics",
        )
    ):
        return 60
    return None


def _get_bucket(bucket_key: str) -> deque:
    """Get or create a bucket for the given key, with automatic TTL eviction.
    
    Uses a lock to ensure thread-safe access to the TTLCache.
    If a key was recently evicted, logs a warning when recreating it.
    """
    with _RATE_BUCKETS_LOCK:
        # If key was recently evicted, log it
        if bucket_key in _EVICTED_KEYS:
            get_logger("RateLimiter").warning(f"Rate bucket recreated after eviction: {bucket_key}")
            _EVICTED_KEYS.discard(bucket_key)
        
        if bucket_key not in _RATE_BUCKETS:
            _RATE_BUCKETS[bucket_key] = deque()
        return _RATE_BUCKETS[bucket_key]


@app.middleware("http")
async def blanket_rate_limit_middleware(request: Request, call_next):
    limit = _resolve_route_limit(request.url.path)
    if not limit:
        return await call_next(request)

    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.client.host if request.client and request.client.host else "unknown"
    bucket_key = f"{client_ip}:{request.method}:{request.url.path}:{limit}"
    
    with _RATE_BUCKETS_LOCK:
        bucket = _get_bucket(bucket_key)
        now_ts = time.time()
        while bucket and (now_ts - bucket[0]) > _RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded: {limit}/minute"},
            )
        bucket.append(now_ts)
    
    return await call_next(request)

APP_ENV = (os.getenv("APP_ENV") or os.getenv("ENV") or "development").strip().lower()
IS_PROD = APP_ENV in {"prod", "production"}


def _init_error_tracking() -> None:
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FastApiIntegration()],
            environment=APP_ENV,
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
        )
        get_logger("ErrorTracking").info("Sentry enabled for environment '%s'", APP_ENV)
    except Exception as exc:
        get_logger("ErrorTracking").warning("Sentry initialization failed: %s", exc)


_init_error_tracking()


def _allowed_cors_origins() -> list[str]:
    configured = [
        origin.strip()
        for origin in (os.getenv("FRONTEND_ORIGINS", "")).split(",")
        if origin.strip()
    ]
    if configured:
        return configured
    if IS_PROD:
        return ["https://kazumee.vercel.app"]
    return [
        "http://localhost:4000",
        "http://127.0.0.1:4000",
        "http://localhost:4001",
        "http://127.0.0.1:4001",
        "http://localhost:4002",
        "http://127.0.0.1:4002",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def _allowed_cors_origin_regex() -> str | None:
    """
    Dev convenience:
    when FRONTEND_ORIGINS is not explicitly configured, allow common LAN origins
    so testing from http://192.168.x.x:<port> works without CORS failures.
    """
    if IS_PROD:
        return None
    return r"^https?://(localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(:\d+)?$"


def _allowed_cors_methods() -> list[str]:
    if IS_PROD:
        return ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    return ["*"]


def _allowed_cors_headers() -> list[str]:
    if IS_PROD:
        return ["Authorization", "Content-Type", "X-Streamer-Id"]
    return ["*"]

# --------------------------------------------------
# CORS
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_cors_origins(),
    allow_origin_regex=_allowed_cors_origin_regex(),
    allow_credentials=True,
    allow_methods=_allowed_cors_methods(),
    allow_headers=_allowed_cors_headers(),
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.get("/")
def root():
    return {"status": "Kazumi backend is running"}

@app.get("/api/auth/session")
async def get_session():
    return {"user": {"name": "Streamer", "email": "admin@kazumi.ai"}, "expires": "9999-12-31T23:59:59.999Z"}

@app.get("/api/auth/csrf")
async def get_csrf():
    return {"csrfToken": secrets.token_urlsafe(24)}

@app.get("/health")
async def health_check(request: Request):
    streamer_mode = getattr(request.app.state, 'streamer_mode', True)
    obs_connected = bool(getattr(obs_bridge, "connected", False))
    return {
        "status": "online",
        "mode": "demo",
        "brain": "deterministic",
        "obs": "connected" if obs_connected else "disconnected",
        "streamer_mode": streamer_mode,
    }

@app.get("/api/health")
async def api_health(request: Request):
    checks = {
        "database": False,
        "obs": False,
        "groq": bool(os.environ.get("GROQ_API_KEY")),
    }

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = True
        finally:
            db.close()
    except Exception:
        checks["database"] = False

    try:
        executor = request.app.state.executor
        obs_status = await executor._get_obs_status()
        checks["obs"] = bool(obs_status.get("connected", False))
    except Exception:
        checks["obs"] = False

    overall = all(checks.values())
    return {"status": "ok" if overall else "degraded", "checks": checks}


# WORKAROUND: Direct routes for /pending and /recent (bypass clips router routing issue)
# TODO: Move back to clips.py once routing is fixed
from backend.database.session import SessionLocal
from backend.database.models.clip import Clip
from backend.database.models.streamer import Streamer

@app.get("/api/clips/pending")
def get_pending_clips_workaround():
	"""Get pending clips - workaround route in main.py"""
	db = SessionLocal()
	try:
		streamer_id = 1
		streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
		if not streamer:
			raise HTTPException(status_code=404, detail="No streamer found")

		clips = db.query(Clip).filter(
			Clip.streamer_id == streamer.id,
			Clip.status == "pending"
		).order_by(Clip.created_at.desc()).all()

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
	finally:
		db.close()


@app.get("/api/clips/recent")
def get_recent_clips_workaround(limit: int = 10):
	"""Get recent approved clips - workaround route in main.py"""
	db = SessionLocal()
	try:
		streamer_id = 1
		streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
		if not streamer:
			raise HTTPException(status_code=404, detail="No streamer found")

		clips = db.query(Clip).filter(
			Clip.streamer_id == streamer.id,
			Clip.status == "approved"
		).order_by(Clip.created_at.desc()).limit(limit).all()

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
	finally:
		db.close()

# v1 Core Routes Only
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(clips.router, prefix="/api/clips", tags=["Clips"])
app.include_router(commands.router, prefix="/commands", tags=["Commands"])
app.include_router(streams.router, prefix="/streams", tags=["Streams"])
app.include_router(moment_finder_router.router, prefix="", tags=["MomentFinder"])
app.include_router(moment_detection_router.router, tags=["MomentDetection"])
app.include_router(settings_router.router, prefix="", tags=["Settings"])
app.include_router(post_stream_report_router.router, prefix="", tags=["PostStreamReport"])
app.include_router(groq_proxy_router.router, tags=["Groq"])
# Removed: companion_router (v1.1+ feature, not needed for v1)
app.include_router(clip_generator_router.router, tags=["ClipGenerator"])
app.include_router(obs_router.router, tags=["OBS"])



# --------------------------------------------------
# API: Analytics (Operational)
# --------------------------------------------------
@app.get("/api/analytics")
async def get_analytics(request: Request, range: str = "7d"):
    # Basic time range handling
    days_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(range, 7)
    since = datetime.utcnow() - timedelta(days=days)

    # Defaults
    analytics = {
        "avgViewers": 0,
        "viewerChange": 0,
        "peakViewers": 0,
        "peakChange": 0,
        "totalMessages": 0,
        "messageChange": 0,
        "streamHours": 0,
        "hoursChange": 0,
        "viewerGrowth": [0] * min(days, 7),
        "engagement": {"chat": 0, "clips": 0, "commands": 0},
        "topClips": [],
        "commands": {"pending": 0, "approved": 0, "rejected": 0, "executed": 0},
        "approvalRate": 0,
        "clips": {"approved": 0, "pending": 0},
        "eventsByPlatform": {},
    }

    _, streamer_id = _require_streamer_access(request)

    try:
        db = SessionLocal()
        try:
            from backend.database.models.stream_session import StreamSession
            from backend.database.models.clip import Clip

            sessions = (
                db.query(StreamSession)
                .filter(StreamSession.start_time >= since)
                .all()
            )
            if streamer_id:
                sessions = [s for s in sessions if s.streamer_id == streamer_id]

            if sessions:
                avg_viewers = [s.avg_viewers or 0 for s in sessions]
                analytics["avgViewers"] = int(sum(avg_viewers) / max(len(avg_viewers), 1))
                analytics["peakViewers"] = int(max(avg_viewers))

                # Compute stream hours
                total_seconds = 0
                for s in sessions:
                    end = s.end_time or datetime.utcnow()
                    total_seconds += max((end - s.start_time).total_seconds(), 0)
                analytics["streamHours"] = round(total_seconds / 3600, 1)

                # Viewer growth (simple bucketing)
                buckets = min(days, 7)
                if buckets > 0:
                    bucket_size = max(int(days / buckets), 1)
                    growth = []
                    for i in range(buckets):
                        start = datetime.utcnow() - timedelta(days=(buckets - i) * bucket_size)
                        end = start + timedelta(days=bucket_size)
                        bucket_sessions = [
                            s for s in sessions if s.start_time >= start and s.start_time < end
                        ]
                        if bucket_sessions:
                            vals = [s.avg_viewers or 0 for s in bucket_sessions]
                            growth.append(int(sum(vals) / len(vals)))
                        else:
                            growth.append(0)
                    analytics["viewerGrowth"] = growth

            # Top clips by quality score (fallback to recent)
            clips_query = db.query(Clip).filter(Clip.created_at >= since)
            if streamer_id:
                clips_query = clips_query.filter(Clip.streamer_id == streamer_id)
            clips = (
                clips_query
                .order_by(Clip.quality_score.desc().nullslast(), Clip.created_at.desc())
                .limit(5)
                .all()
            )

            analytics["topClips"] = [
                {
                    "title": c.title or "Untitled Clip",
                    "views": int((c.quality_score or 0) * 100),
                    "score": int((c.quality_score or 0) * 10),
                    "detection": "AI",
                }
                for c in clips
            ]

            # Engagement approximations
            commands_query = db.query(CommandModel)
            if streamer_id:
                commands_query = commands_query.filter(CommandModel.streamer_id == streamer_id)
            commands_count = commands_query.count()
            pending_count = commands_query.filter(CommandModel.status == "pending").count()
            approved_count = commands_query.filter(CommandModel.status == "approved").count()
            rejected_count = commands_query.filter(CommandModel.status == "rejected").count()
            executed_count = commands_query.filter(CommandModel.status == "executed").count()
            analytics["commands"] = {
                "pending": pending_count,
                "approved": approved_count,
                "rejected": rejected_count,
                "executed": executed_count,
            }
            approval_denom = approved_count + rejected_count
            analytics["approvalRate"] = int((approved_count / approval_denom) * 100) if approval_denom else 0
            from backend.database.models.stream_event import StreamEvent

            events_query = db.query(StreamEvent).filter(StreamEvent.created_at >= since)
            if streamer_id:
                events_query = events_query.filter(StreamEvent.streamer_id == streamer_id)
            total_events = events_query.count()
            analytics["totalMessages"] = total_events
            platform_rows = (
                events_query
                .with_entities(StreamEvent.platform, func.count(StreamEvent.id))
                .group_by(StreamEvent.platform)
                .all()
            )
            analytics["eventsByPlatform"] = {p: c for p, c in platform_rows}

            taste_tags = []
            if streamer_id:
                streamer = db.query(StreamerModel).filter(StreamerModel.id == streamer_id).first()
                if streamer and streamer.taste_profile:
                    tag_counts = streamer.taste_profile.get("tags") or {}
                    taste_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            analytics["tasteTags"] = taste_tags

            clip_approved = db.query(Clip).filter(Clip.status == "approved").count()
            clip_pending = db.query(Clip).filter(Clip.status == "pending").count()
            if streamer_id:
                clip_approved = db.query(Clip).filter(Clip.status == "approved", Clip.streamer_id == streamer_id).count()
                clip_pending = db.query(Clip).filter(Clip.status == "pending", Clip.streamer_id == streamer_id).count()
            analytics["clips"] = {"approved": clip_approved, "pending": clip_pending}

            analytics["engagement"] = {
                "chat": min(100, total_events),
                "clips": min(100, clip_approved + clip_pending),
                "commands": min(100, commands_count),
            }

        finally:
            db.close()
    except Exception:
        # Fallback is already populated
        pass

    return analytics

# --------------------------------------------------
# API: Stream Health (Operational)
# --------------------------------------------------
@app.get("/api/stream-health")
async def get_stream_health(request: Request):
    # Local machine baseline (TODO: add real monitoring in v1.1)
    system_cpu = 0.0
    system_mem = 0.0

    executor = getattr(request.app.state, "executor", None)
    obs_status = {"connected": False, "streaming": False, "recording": False}
    obs_stats = {}
    if executor:
        try:
            obs_status = await executor._get_obs_status()
        except Exception:
            obs_status = {"connected": False, "streaming": False, "recording": False}
        try:
            if executor.obs:
                obs_stats = await executor.obs.get_stats()
        except Exception:
            obs_stats = {}

    obs_connected = bool(obs_status.get("connected", False))
    obs_error = bool(obs_stats.get("error"))

    cpu = float(obs_stats.get("cpu_usage") or system_cpu)
    mem = float(obs_stats.get("memory_usage") or system_mem)
    gpu = float(obs_stats.get("gpu_usage") or 0.0)
    bitrate = float(obs_stats.get("bitrate") or 0.0)
    dropped_frames = int(obs_stats.get("dropped_frames") or 0)
    latency_ms = int(obs_stats.get("network_latency_ms") or 0)
    if latency_ms <= 0:
        latency_ms = int(float(obs_stats.get("output_congestion") or 0.0) * 120.0)
    if latency_ms <= 0:
        latency_ms = 12

    reconnecting = bool(obs_stats.get("output_reconnecting", False))
    mic_muted = bool(obs_stats.get("mic_muted", False))

    health_status = "healthy"
    if (not obs_connected and obs_error) or reconnecting or cpu >= 95 or mem >= 95 or dropped_frames >= 180:
        health_status = "critical"
    elif cpu >= 85 or mem >= 85 or latency_ms >= 80 or dropped_frames >= 60:
        health_status = "warning"

    predictions = []
    if reconnecting:
        predictions.append(
            {"message": "OBS output is reconnecting. Verify upload stability immediately.", "severity": "high", "confidence": 95}
        )
    if dropped_frames >= 60:
        rec = max(2500, min(6000, int((bitrate or 6000) - 1000)))
        predictions.append(
            {
                "message": f"Dropped frames detected ({dropped_frames}). Suggested bitrate: {rec} kbps.",
                "severity": "high" if dropped_frames >= 120 else "medium",
                "confidence": 88 if dropped_frames >= 120 else 79,
            }
        )
    if cpu >= 85:
        predictions.append({"message": f"CPU usage is high ({cpu:.0f}%).", "severity": "medium", "confidence": 84})
    if mem >= 85:
        predictions.append({"message": f"Memory pressure detected ({mem:.0f}%).", "severity": "medium", "confidence": 78})
    if mic_muted:
        predictions.append({"message": "Mic source appears muted.", "severity": "high", "confidence": 97})
    if not predictions:
        predictions.append({"message": "Stream health looks stable.", "severity": "low", "confidence": 92})

    # Actionable health rules
    from backend.core.health_rules import evaluate_health, filter_actions

    metrics = {
        "cpu": cpu,
        "mem": mem,
        "latency_ms": latency_ms,
        "bitrate_kbps": bitrate,
        "obs_connected": obs_connected,
        "auto_apply": os.getenv("STREAM_DOCTOR_AUTO_APPLY", "false").lower() == "true",
    }
    actions = filter_actions(evaluate_health(metrics))

    # Persist actionable suggestions for streamer dashboards.
    streamer_id = None
    try:
        _, streamer_id = _require_streamer_access(request)
    except HTTPException:
        streamer_id = None

    if streamer_id and actions:
        db = SessionLocal()
        try:
            session = _get_or_create_stream_session(db, streamer_id=streamer_id)
            for action in actions:
                cmd = CommandModel(
                    stream_session_id=session.id,
                    streamer_id=session.streamer_id,
                    issued_by_type="health_engine",
                    issued_by_id=None,
                    command_text=f"Health Action: {action.action}",
                    intent=action.action,
                    ai_reasoning=action.reason,
                    confidence_score=action.confidence,
                    status="pending",
                    priority_level=80 if action.severity == "high" else 50,
                )
                db.add(cmd)
            db.commit()
        finally:
            db.close()

    # Execute auto actions when explicitly marked executable.
    for action in actions:
        if action.execute and executor:
            try:
                await executor.execute(action.action, action.payload or {})
            except Exception:
                pass

    # Trend detection across the previous sample
    previous = getattr(request.app.state, "health_last_sample", None)

    def _trend(curr: float, prev: float | None, tolerance: float = 0.05) -> str:
        if prev is None:
            return "stable"
        baseline = max(abs(prev), 1.0)
        delta = (curr - prev) / baseline
        if delta > tolerance:
            return "up"
        if delta < -tolerance:
            return "down"
        return "stable"

    stress = min(
        1.0,
        (cpu / 100.0) * 0.35
        + (mem / 100.0) * 0.25
        + (min(latency_ms, 200) / 200.0) * 0.15
        + (min(dropped_frames, 240) / 240.0) * 0.25,
    )
    prediction_score = int(max(1, min(99, round((1.0 - stress) * 100))))

    bitrate_trend = _trend(bitrate, previous.get("bitrate") if previous else None, tolerance=0.08)
    dropped_trend = _trend(float(dropped_frames), previous.get("dropped_frames") if previous else None, tolerance=0.12)
    prediction_trend = _trend(float(prediction_score), previous.get("prediction_score") if previous else None, tolerance=0.03)

    request.app.state.health_last_sample = {
        "bitrate": float(bitrate),
        "dropped_frames": float(dropped_frames),
        "prediction_score": float(prediction_score),
    }

    return {
        "healthStatus": health_status,
        "cpuUsage": round(cpu, 1),
        "gpuUsage": round(gpu, 1),
        "memoryUsage": round(mem, 1),
        "networkLatency": int(latency_ms),
        "bitrate": round(bitrate, 1),
        "bitrateTrend": bitrate_trend,
        "droppedFrames": dropped_frames,
        "droppedFramesTrend": dropped_trend,
        "predictionScore": prediction_score,
        "predictionTrend": prediction_trend,
        "predictions": predictions[:5],
        "actions": [
            {
                "action": a.action,
                "reason": a.reason,
                "confidence": a.confidence,
                "severity": a.severity,
                "execute": a.execute,
                "payload": a.payload or {},
            }
            for a in actions
        ],
        "obsConnected": obs_connected,
        "streaming": bool(obs_status.get("streaming", False)),
        "recording": bool(obs_status.get("recording", False)),
        "micMuted": mic_muted,
    }

# --------------------------------------------------
# API: Command Queue (Operational)
# --------------------------------------------------
@app.get("/api/commands")
async def get_command_queue(request: Request, status: str = "all", tier: str = "all"):
    _, streamer_id = _require_streamer_access(request)

    try:
        db = SessionLocal()
        try:
            query = db.query(CommandModel)
            if streamer_id:
                query = query.filter(CommandModel.streamer_id == streamer_id)
            if status != "all":
                query = query.filter(CommandModel.status == status)
            commands = query.order_by(CommandModel.created_at.desc()).all()
            items = [_serialize_command(c) for c in commands]
            if tier != "all":
                items = [c for c in items if c["viewer_tier"] == tier]
            return {"commands": items}
        finally:
            db.close()
    except Exception:
        items = command_queue
        if status != "all":
            items = [c for c in items if c["status"] == status]
        if tier != "all":
            items = [c for c in items if c["viewer_tier"] == tier]
        return {"commands": items}

@app.post("/api/commands/{command_id}/execute")
async def execute_queued_command(command_id: int, request: Request):
    _, streamer_id = _require_streamer_access(request)
    db = SessionLocal()
    try:
        cmd = (
            db.query(CommandModel)
            .filter(
                CommandModel.id == command_id,
                CommandModel.streamer_id == streamer_id,
            )
            .first()
        )
        if not cmd:
            return {"status": "error", "message": "Command not found"}
        if (cmd.status or "pending") != "pending":
            return {"status": "error", "message": "Command has already been handled"}

        item = _serialize_command(cmd)
        executor = request.app.state.executor
        obs_status = await executor._get_obs_status()
        live_scenes = obs_status.get("scenes", ["Gameplay", "Chat", "Break"])
        decision = brain_decider.decide(item["command_text"], live_scenes)

        if decision.decision == "execute" and decision.action:
            action_name = decision.action.value
            result = await executor.execute(action_name, decision.payload or {})
            cmd.status = "executed" if result.status == "ok" else "error"
            cmd.intent = action_name
            cmd.ai_reasoning = decision.reason
            cmd.confidence_score = decision.confidence
            db.commit()
            event_log.insert(
                0,
                {
                    "type": "system_action",
                    "description": item["command_text"],
                    "commentary": result.message,
                    "time": datetime.now().strftime("%H:%M"),
                    "status": "completed" if result.status == "ok" else "error",
                },
            )
            return {"status": "success", "result": result}

        cmd.status = "rejected"
        db.commit()
        return {"status": "error", "message": decision.reason}
    finally:
        db.close()

@app.post("/api/commands/{command_id}/reject")
async def reject_queued_command(command_id: int, request: Request):
    _, streamer_id = _require_streamer_access(request)
    db = SessionLocal()
    try:
        cmd = (
            db.query(CommandModel)
            .filter(
                CommandModel.id == command_id,
                CommandModel.streamer_id == streamer_id,
            )
            .first()
        )
        if not cmd:
            return {"status": "error", "message": "Command not found"}
        cmd.status = "rejected"
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

# --------------------------------------------------
# API: Settings (Operational)
# --------------------------------------------------
@app.get("/api/settings")
async def get_settings(request: Request):
    _require_streamer_access(request)
    return settings_store

@app.put("/api/settings")
async def update_settings(payload: dict, request: Request):
    _require_streamer_access(request)
    settings_store.update(payload)
    return {"status": "success"}

@app.post("/command")
async def handle_voice_command(request: Request):
    body = await request.json()
    user_text = body.get("text", "")

    executor = request.app.state.executor
    _require_streamer_access(request)

    # 1. Fetch current OBS scenes to help the brain decide
    obs_status = await executor._get_obs_status()
    live_scenes = obs_status.get("scenes", ["Gameplay", "Chat", "Break"])

    # 2. Brain makes the decision
    decision = brain_decider.decide(user_text, live_scenes)

    # 3. If valid OBS command, Execute
    if decision.decision == "execute" and decision.action:
        # decision.action.value gives the string like "start_recording"
        result = await executor.execute(decision.action.value, decision.payload or {})
        return {"status": "success", "result": result}

    # 4. If unknown command, route to LLM for chat
    if decision.decision == "refuse":
        try:
            # Get command service from app state (assuming it's initialized in lifespan)
            command_service = request.app.state.command_service

            # Process with AI (LLM fallback)
            ai_response = await command_service._process_with_ai(user_text, is_event=False)

            if ai_response.get("success"):
                links = await search_links(user_text, limit=2)
                links_text = format_links_for_chat(links)
                message = ai_response.get("commentary", "I heard you, but I'm not sure what to do.")
                if links_text:
                    message = message + "\n\n" + links_text
                return {
                    "status": "chat",
                    "message": message,
                    "intent": ai_response.get("intent", "chat")
                }
            else:
                return {
                    "status": "chat",
                    "message": "I'm having trouble connecting to my brain right now. Try again later.",
                    "intent": "error"
                }
        except Exception as e:
            return {
                "status": "chat",
                "message": "Sorry, I encountered an error processing your request.",
                "intent": "error"
            }

    return {"status": "ignored", "reason": decision.reason}

# 2. Create the route you called in page.jsx
@app.post("/api/commands/process")
async def process_command(data: dict, request: Request):
    user_msg = data.get("command", "")
    role = data.get("role", "viewer")
    streamer_mode = getattr(request.app.state, 'streamer_mode', True)
    user = get_current_user(request, required=True)
    if user and user.role:
        role = user.role
    streamer_id = resolve_streamer_id(request, user)
    if role == "streamer" and not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    # Viewer quota enforcement driven by backend/config/pricing.json
    if user and role == "viewer":
        db = SessionLocal()
        try:
            viewer = db.query(ViewerModel).filter(ViewerModel.user_id == user.id).first()
            if viewer:
                violation = limit_violation(
                    db=db,
                    viewer_id=viewer.id,
                    viewer_tier=viewer.tier,
                    action_type="submit_command",
                    limit_key="commands_per_day",
                    period="day",
                )
                if violation:
                    raise HTTPException(status_code=429, detail=violation["message"])

                if streamer_id:
                    db.add(
                        ViewerAction(
                            streamer_id=streamer_id,
                            viewer_id=viewer.id,
                            action_type="submit_command",
                            target=(user_msg or "")[:180],
                            cost=0,
                            status="queued",
                        )
                    )
                    db.commit()
        finally:
            db.close()

    # Check if streamer mode is enabled and role is not streamer
    if streamer_mode and role != "streamer":
        # Streamer mode enabled, viewer role: Use Groq for lore/questions only, no OBS actions
        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": """You are Kazumi, a helpful AI assistant for stream viewers. You can help with:
                - Answering questions about stream lore and history
                - Explaining memes, inside jokes, or references from the stream
                - Discussing clip suggestions and highlights
                - Providing information about the streamer or stream content
                - Engaging in friendly chat about the stream

                IMPORTANT: You CANNOT control OBS or perform any streaming actions. If asked about technical controls, politely explain you don't have access to those features in viewer mode.

                Keep responses friendly, engaging, and focused on stream-related topics."""},
                {"role": "user", "content": user_msg}
            ]
        )
        clean_text = completion.choices[0].message.content.strip()
        links = await search_links(user_msg, limit=2)
        links_text = format_links_for_chat(links)
        if links_text:
            clean_text = clean_text + "\n\n" + links_text

        # Log viewer interaction
        new_event = {
            "type": "viewer_msg",
            "description": user_msg,
            "commentary": clean_text,
            "time": datetime.now().strftime("%H:%M"),
            "status": "completed"
        }
        event_log.insert(0, new_event)
        if len(event_log) > 50:
            event_log.pop()

        return {"message": clean_text}

    # Streamer mode or streamer role: Use brain decider for OBS actions
    executor = request.app.state.executor

    # 1. Fetch current OBS scenes to help the brain decide
    obs_status = await executor._get_obs_status()
    live_scenes = obs_status.get("scenes", ["Gameplay", "Chat", "Break"])

    # 2. Brain makes the decision
    decision = brain_decider.decide(user_msg, live_scenes)

    # Viewer clipping is primary-only (Twitch Helix Create Clip). Do not fall back to OBS/local clipping.
    if (
        role == "viewer"
        and decision.decision == "execute"
        and decision.action in {BrainAction.SAVE_REPLAY_BUFFER, BrainAction.CREATE_CLIP}
    ):
        return {
            "message": "Viewer clipping is primary-only. Use Twitch integration (clips:edit + broadcaster_id). Secondary OBS clipping is disabled for viewers."
        }

    # Clip cooldown for viewers
    global last_clip_time
    if decision.decision == "execute" and decision.action == BrainAction.SAVE_REPLAY_BUFFER and role == "viewer":
        if last_clip_time and (datetime.now() - last_clip_time).total_seconds() < 120:
            return {"message": "Clip cooldown active. Please wait 2 minutes before clipping again."}
        last_clip_time = datetime.now()

    # 3. If valid command, execute it (policy-aware)
    if decision.decision == "execute" and decision.action:
        action_name = decision.action.value
        min_conf = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
        min_sensitive = float(os.getenv("CONFIDENCE_THRESHOLD_SENSITIVE", "0.9"))
        confidence = getattr(decision, "confidence", 0.0) or 0.0
        sensitive_actions = {"panic_mode", "start_streaming", "stop_streaming", "restart_engine"}
        if action_name in sensitive_actions and confidence < min_sensitive:
            _enqueue_command(
                user_msg,
                streamer_id=streamer_id,
                intent=action_name,
                ai_reasoning=decision.reason,
                confidence_score=confidence,
            )
            return {
                "message": "Low confidence for sensitive action. Queued for approval.",
                "confidence": confidence,
            }
        if confidence < min_conf and role != "streamer":
            _enqueue_command(
                user_msg,
                streamer_id=streamer_id,
                intent=action_name,
                ai_reasoning=decision.reason,
                confidence_score=confidence,
            )
            return {"message": "Low confidence. Queued for approval.", "confidence": confidence}

        policy = evaluate_action(action_name, role, streamer_id=streamer_id)
        if policy == "deny":
            return {"message": "This action is restricted to the streamer."}
        if policy == "approve":
            _enqueue_command(
                user_msg,
                streamer_id=streamer_id,
                intent=action_name,
                ai_reasoning=decision.reason,
                confidence_score=confidence,
            )
            return {"message": "Request queued for streamer approval."}
        if role == "streamer" and action_name in OBS_CONFIRMATION_ACTIONS and not data.get("confirmed"):
            _enqueue_command(
                user_msg,
                viewer_username="streamer",
                viewer_tier="vip",
                streamer_id=streamer_id,
                intent=action_name,
                ai_reasoning=decision.reason,
                confidence_score=confidence,
            )
            return {
                "message": "OBS action queued for confirmation.",
                "execution_status": "pending_approval",
                "resolved_intent": action_name,
                "confidence": confidence,
            }
        result = await executor.execute(decision.action.value, decision.payload or {})

        # SILENT SUCCESS RESPONSE for OBS actions
        if result.status == "ok" and not result.message.strip():
            return {
                "success": True,
                "silent": True,
                "actions": [decision.action.value],
                "message": ""  # Empty message prevents chat bubble
            }

        # Log successful execution
        new_event = {
            "type": "system_action",
            "description": user_msg,
            "commentary": result.message,
            "time": datetime.now().strftime("%H:%M"),
            "status": "completed"
        }
        event_log.insert(0, new_event)
        if len(event_log) > 50:
            event_log.pop()

        return {"message": result.message}

    # 4. If unknown command, route to LLM for chat
    if decision.decision == "refuse":
        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Kazumi, a helpful AI assistant. Keep responses friendly and engaging."},
                {"role": "user", "content": user_msg}
            ]
        )
        clean_text = completion.choices[0].message.content.strip()
        links = await search_links(user_msg, limit=2)
        links_text = format_links_for_chat(links)
        if links_text:
            clean_text = clean_text + "\n\n" + links_text

        # Log chat response
        new_event = {
            "type": "system_action",
            "description": user_msg,
            "commentary": clean_text,
            "time": datetime.now().strftime("%H:%M"),
            "status": "completed"
        }
        event_log.insert(0, new_event)
        if len(event_log) > 50:
            event_log.pop()

        return {"message": clean_text}

    return {"message": "Command not recognized"}

# Optional: Clear History
@app.post("/api/commands/clear")
async def clear_logs(request: Request):
    _require_streamer_access(request)
    global event_log
    event_log = []
    return {"status": "success"}

@app.get("/events/log")
async def get_event_log(request: Request):
    _require_streamer_access(request)
    return {"events": event_log}

@app.get("/api/viewer/dashboard")
async def get_viewer_dashboard(request: Request):
    from backend.database.models.viewer import Viewer as ViewerModel
    from backend.database.models.clip import Clip as ClipModel
    from backend.database.models.streamer import Streamer as StreamerModel
    from backend.database.models.stream_session import StreamSession as StreamSessionModel
    from backend.database.models.stream_event import StreamEvent as StreamEventModel

    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    db = SessionLocal()
    try:
        viewer = None
        if user and user.role == "viewer":
            viewer = db.query(ViewerModel).filter(ViewerModel.user_id == user.id).first()
            if not streamer_id and viewer:
                streamer_id = viewer.active_streamer_id

        if user.role == "streamer" and not streamer_id:
            raise HTTPException(status_code=400, detail="streamer_id required")

        active_streamer = None
        live_session = None
        if streamer_id:
            active_streamer = db.query(StreamerModel).filter(StreamerModel.id == streamer_id).first()
            live_session = (
                db.query(StreamSessionModel)
                .filter(
                    StreamSessionModel.streamer_id == streamer_id,
                    StreamSessionModel.status == "live",
                )
                .order_by(StreamSessionModel.start_time.desc())
                .first()
            )

        total_messages = 0
        recent_chat_events = 0
        recent_hype_signals = 0
        if streamer_id:
            total_messages = (
                db.query(func.count(StreamEventModel.id))
                .filter(StreamEventModel.streamer_id == streamer_id)
                .scalar()
                or 0
            )
            recent_window = datetime.utcnow() - timedelta(minutes=10)
            recent_rows = (
                db.query(StreamEventModel)
                .filter(
                    StreamEventModel.streamer_id == streamer_id,
                    StreamEventModel.created_at >= recent_window,
                )
                .order_by(StreamEventModel.created_at.desc())
                .limit(400)
                .all()
            )
            recent_chat_events = len(
                [
                    row
                    for row in recent_rows
                    if (row.message or "").strip()
                    or (row.event_type or "").startswith("chat")
                ]
            )
            recent_hype_signals = len(
                [
                    row
                    for row in recent_rows
                    if any(
                        token in ((row.message or "").lower())
                        for token in ["wow", "omg", "insane", "clip", "clutch", "gg", "lets go", "pog"]
                    )
                    or (row.event_type or "") in {"clip_created", "viewer_clip_ready", "viewer_impact"}
                ]
            )

        clips_query = db.query(ClipModel).order_by(ClipModel.created_at.desc())
        if streamer_id:
            clips_query = clips_query.filter(ClipModel.streamer_id == streamer_id)
        if viewer:
            clips_query = clips_query.filter(
                (ClipModel.requested_by_id == str(viewer.id))
                | (ClipModel.requested_by_name == viewer.username)
            )
        clips = clips_query.limit(4).all()
        if not clips and streamer_id:
            clips = (
                db.query(ClipModel)
                .filter(ClipModel.streamer_id == streamer_id)
                .order_by(ClipModel.created_at.desc())
                .limit(4)
                .all()
            )

        vibe_label = "quiet"
        if recent_hype_signals >= 14 or recent_chat_events >= 80:
            vibe_label = "hyped"
        elif recent_hype_signals >= 7 or recent_chat_events >= 40:
            vibe_label = "intense"
        elif recent_chat_events >= 15:
            vibe_label = "chill"

        kazumi_active = bool(streamer_id and (recent_chat_events > 0 or recent_hype_signals > 0))

        return {
            "active_streamer_id": streamer_id,
            "active_streamer": {
                "id": active_streamer.id,
                "display_name": active_streamer.display_name or active_streamer.username,
                "username": active_streamer.username,
                "platform": active_streamer.platform,
            } if active_streamer else None,
            "viewer": {
                "id": str(viewer.id) if viewer else "guest",
                "tier": viewer.tier if viewer and viewer.tier else "free",
            },
            "currentStream": {
                "id": str(live_session.id) if live_session else None,
                "title": "Live Stream" if live_session else "No live stream right now",
                "viewer_count": int(live_session.avg_viewers or 0) if live_session else 0,
                "total_messages": int(total_messages),
            } if streamer_id else None,
            "kazumi_active": kazumi_active,
            "stream_vibe": {
                "label": vibe_label,
                "chat_events_10m": int(recent_chat_events),
                "hype_signals_10m": int(recent_hype_signals),
            } if streamer_id else None,
            "yourClips": [
                {
                    "id": clip.id,
                    "title": clip.title or f"Clip #{clip.id}",
                    "url": clip.file_path,
                    "thumbnail_url": clip.thumbnail_path,
                    "moment_label": (clip.tags[0] if isinstance(clip.tags, list) and clip.tags else None),
                    "status": clip.status,
                }
                for clip in clips
            ],
            "loreSuggestions": [
                "What happened in the last big clutch?",
                "Recap the best moments from this stream",
                "Explain the running joke in chat",
            ],
        }
    finally:
        db.close()


def _require_streamer_access(request: Request):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")
    return user, streamer_id

@app.get("/api/dashboard")
async def get_main_dashboard(request: Request):
    user, streamer_id = _require_streamer_access(request)
    from backend.database.models.clip import Clip as ClipModel
    from backend.database.models.stream_event import StreamEvent as StreamEventModel
    from backend.database.models.platform_connection import PlatformConnection as PlatformConnectionModel

    def _signed_percent_delta(current: float, previous: float) -> str:
        if previous <= 0:
            if current <= 0:
                return "+0%"
            return "+100%"
        return f"{((current - previous) / previous) * 100:+.0f}%"

    def _pulse_label(score: int) -> str:
        if score >= 75:
            return "strong"
        if score >= 50:
            return "stable"
        if score >= 30:
            return "warming_up"
        return "at_risk"

    def classify_activity(item: dict) -> tuple[str, str | None, str | None]:
        if item.get("was_auto_handled"):
            return "handled", None, None
        if item.get("requires_streamer_response"):
            event_type = str(item.get("type") or "").lower()
            if event_type.startswith("moderation_"):
                return "needs_you", "Open moderation", "/moderation"
            return "needs_you", "Review now", "/commands"
        return "watching", None, None

    executor = getattr(request.app.state, "executor", None)
    obs_status: Dict[str, Any] = {"connected": False, "streaming": False, "recording": False}
    obs_stats: Dict[str, Any] = {}
    if executor:
        try:
            obs_status = await executor._get_obs_status()
        except Exception:
            obs_status = {"connected": False, "streaming": False, "recording": False}
        try:
            if getattr(executor, "obs", None):
                obs_stats = await executor.obs.get_stats()
        except Exception:
            obs_stats = {}

    obs_connected = bool(obs_status.get("connected", False))
    cpu_usage = float(obs_stats.get("cpu_usage") or 0.0)
    mem_usage = float(obs_stats.get("memory_usage") or 0.0)
    dropped_frames = int(obs_stats.get("dropped_frames") or 0)
    bitrate_kbps = float(obs_stats.get("bitrate") or 0.0)

    stress = min(
        1.0,
        (cpu_usage / 100.0) * 0.45
        + (mem_usage / 100.0) * 0.35
        + (min(dropped_frames, 240) / 240.0) * 0.2,
    )
    health_score = int(max(1, min(99, round((1.0 - stress) * 100))))
    if not obs_connected:
        health_status = "OBS Disconnected"
    elif health_score >= 80:
        health_status = "Optimal"
    elif health_score >= 60:
        health_status = "Warning"
    else:
        health_status = "Critical"

    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)
    since_48h = now - timedelta(hours=48)

    db = SessionLocal()
    try:
        live_session = (
            db.query(StreamSessionModel)
            .filter(
                StreamSessionModel.streamer_id == streamer_id,
                StreamSessionModel.status == "live",
            )
            .order_by(StreamSessionModel.start_time.desc())
            .first()
        )
        current_viewers = int(live_session.avg_viewers or 0) if live_session else 0

        avg_viewers_24h = float(
            db.query(func.coalesce(func.avg(StreamSessionModel.avg_viewers), 0.0))
            .filter(
                StreamSessionModel.streamer_id == streamer_id,
                StreamSessionModel.start_time >= since_24h,
            )
            .scalar()
            or 0.0
        )
        avg_viewers_prev_24h = float(
            db.query(func.coalesce(func.avg(StreamSessionModel.avg_viewers), 0.0))
            .filter(
                StreamSessionModel.streamer_id == streamer_id,
                StreamSessionModel.start_time >= since_48h,
                StreamSessionModel.start_time < since_24h,
            )
            .scalar()
            or 0.0
        )
        viewer_change = _signed_percent_delta(avg_viewers_24h, avg_viewers_prev_24h)

        clips_24h_q = db.query(ClipModel).filter(
            ClipModel.streamer_id == streamer_id,
            ClipModel.created_at >= since_24h,
        )
        clips_total_24h = clips_24h_q.count()
        auto_clips = clips_24h_q.filter(
            ClipModel.requested_by_type.in_(["ai", "ai_observer", "system", "agent"])
        ).count()
        manual_clips = clips_24h_q.filter(
            ClipModel.requested_by_type.in_(["viewer", "streamer"])
        ).count()
        if auto_clips + manual_clips < clips_total_24h:
            auto_clips += clips_total_24h - (auto_clips + manual_clips)

        mod_events = (
            db.query(func.count(StreamEventModel.id))
            .filter(
                StreamEventModel.streamer_id == streamer_id,
                StreamEventModel.created_at >= since_24h,
                StreamEventModel.event_type.like("moderation_%"),
            )
            .scalar()
            or 0
        )
        auto_moderated_events = (
            db.query(func.count(StreamEventModel.id))
            .filter(
                StreamEventModel.streamer_id == streamer_id,
                StreamEventModel.created_at >= since_24h,
                StreamEventModel.event_type == "moderation_allowed",
            )
            .scalar()
            or 0
        )
        auto_moderated = int(round((auto_moderated_events / mod_events) * 100)) if mod_events else 0

        since_10m = now - timedelta(minutes=10)
        since_5m = now - timedelta(minutes=5)
        since_15m = now - timedelta(minutes=15)
        since_20m = now - timedelta(minutes=20)
        chat_5m = (
            db.query(func.count(StreamEventModel.id))
            .filter(
                StreamEventModel.streamer_id == streamer_id,
                StreamEventModel.created_at >= since_5m,
                StreamEventModel.message.isnot(None),
            )
            .scalar()
            or 0
        )
        chat_prev_5m = (
            db.query(func.count(StreamEventModel.id))
            .filter(
                StreamEventModel.streamer_id == streamer_id,
                StreamEventModel.created_at >= since_10m,
                StreamEventModel.created_at < since_5m,
                StreamEventModel.message.isnot(None),
            )
            .scalar()
            or 0
        )
        viewer_actions_10m = (
            db.query(func.count(ViewerAction.id))
            .filter(
                ViewerAction.streamer_id == streamer_id,
                ViewerAction.created_at >= since_10m,
            )
            .scalar()
            or 0
        )
        viewer_actions_prev_10m = (
            db.query(func.count(ViewerAction.id))
            .filter(
                ViewerAction.streamer_id == streamer_id,
                ViewerAction.created_at >= since_20m,
                ViewerAction.created_at < since_10m,
            )
            .scalar()
            or 0
        )

        def _compute_pulse(viewer_count: float, chat_count_5m: float, health_pct: float, action_count_10m: float) -> int:
            viewer_score = min(30.0, max(0.0, (viewer_count / 100.0) * 30.0))
            chat_per_min = chat_count_5m / 5.0
            chat_score = min(25.0, max(0.0, chat_per_min * 3.0))
            health_component = max(0.0, min(100.0, health_pct)) * 0.25
            engagement_rate = action_count_10m / max(viewer_count, 1.0)
            engagement_score = min(20.0, max(0.0, engagement_rate * 40.0))
            return int(max(0.0, min(100.0, round(viewer_score + chat_score + health_component + engagement_score))))

        baseline_viewers = float(avg_viewers_24h or 0.0)
        pulse_score = _compute_pulse(float(current_viewers), float(chat_5m), float(health_score), float(viewer_actions_10m))
        pulse_prev = _compute_pulse(
            baseline_viewers,
            float(chat_prev_5m),
            float(health_score),
            float(viewer_actions_prev_10m),
        )
        pulse_trend = int(pulse_score - pulse_prev)

        pending_commands = (
            db.query(func.count(CommandModel.id))
            .filter(
                CommandModel.streamer_id == streamer_id,
                CommandModel.status == "pending",
            )
            .scalar()
            or 0
        )

        streamer = db.query(StreamerModel).filter(StreamerModel.id == streamer_id).first()
        user_name = (
            streamer.display_name
            if streamer and streamer.display_name
            else streamer.username
            if streamer and streamer.username
            else user.email
        )
        taste_profile = (streamer.taste_profile or {}) if streamer else {}
        approved = int(taste_profile.get("approved") or 0)
        rejected = int(taste_profile.get("rejected") or 0)
        if approved + rejected > 0:
            ml_confidence = int(round((approved / max(approved + rejected, 1)) * 100))
        else:
            avg_command_conf = (
                db.query(func.avg(CommandModel.confidence_score))
                .filter(CommandModel.streamer_id == streamer_id)
                .scalar()
            )
            avg_clip_quality = (
                db.query(func.avg(ClipModel.quality_score))
                .filter(
                    ClipModel.streamer_id == streamer_id,
                    ClipModel.quality_score.isnot(None),
                )
                .scalar()
            )
            confidence_samples = []
            if avg_command_conf is not None:
                confidence_samples.append(float(avg_command_conf))
            if avg_clip_quality is not None:
                confidence_samples.append(float(avg_clip_quality))
            ml_confidence = (
                int(round((sum(confidence_samples) / len(confidence_samples)) * 100))
                if confidence_samples
                else 0
            )

        recent_events = (
            db.query(StreamEventModel)
            .filter(StreamEventModel.streamer_id == streamer_id)
            .order_by(StreamEventModel.created_at.desc())
            .limit(12)
            .all()
        )
        recent_commands = (
            db.query(CommandModel)
            .filter(CommandModel.streamer_id == streamer_id)
            .order_by(CommandModel.created_at.desc())
            .limit(8)
            .all()
        )
        recent_activity = []
        
        # List of event types that are NOT important enough for the feed
        UNIMPORTANT_EVENT_TYPES = {
            "chat_message",
            "viewer_message", 
            "platform_message",
            "raid",
            "follow",
            "subscribe",
            "cheer",
            "gift",
            "watching",
            "view",
            "unknown",
        }
        
        for evt in recent_events:
            evt_type = (evt.event_type or "").lower()
            
            # Skip unimportant event types to reduce feed noise
            if evt_type in UNIMPORTANT_EVENT_TYPES:
                continue
                
            evt_payload = evt.payload or {}
            was_auto_handled = bool(
                evt_payload.get("was_auto_handled")
                or (evt.event_type or "").lower() in {"clip_created", "viewer_clip_ready", "viewer_impact"}
            )
            requires_streamer_response = bool(
                evt_payload.get("requires_streamer_response")
                or (evt.event_type or "").lower().startswith("moderation_flagged")
            )
            activity = {
                "type": evt.event_type or "event",
                "description": (evt.username or "system"),
                "commentary": evt.message or f"{evt.platform} event captured",
                "time": evt.created_at.strftime("%H:%M") if evt.created_at else datetime.now().strftime("%H:%M"),
                "status": "completed",
                "was_auto_handled": was_auto_handled,
                "requires_streamer_response": requires_streamer_response,
                "_ts": evt.created_at or now,
            }
            action_type, action_label, action_href = classify_activity(activity)
            recent_activity.append(
                {
                    **activity,
                    "action_type": action_type,
                    "action_label": action_label,
                    "action_href": action_href,
                }
            )
        
        for cmd in recent_commands:
            cmd_status = (cmd.status or "pending").lower()
            
            # Only include important command statuses
            if cmd_status not in {"pending", "queued", "executed", "approved", "completed", "error"}:
                continue
                
            activity = {
                "type": "system_action",
                "description": cmd.command_text or "Command",
                "commentary": cmd.ai_reasoning or f"Status: {cmd.status or 'pending'}",
                "time": cmd.created_at.strftime("%H:%M") if cmd.created_at else datetime.now().strftime("%H:%M"),
                "status": cmd.status or "pending",
                "was_auto_handled": cmd_status in {"executed", "approved", "completed"},
                "requires_streamer_response": cmd_status in {"pending", "queued"},
                "_ts": cmd.created_at or now,
            }
            action_type, action_label, action_href = classify_activity(activity)
            recent_activity.append(
                {
                    **activity,
                    "action_type": action_type,
                    "action_label": action_label,
                    "action_href": action_href,
                }
            )
        recent_activity.sort(key=lambda item: item.get("_ts", now), reverse=True)
        for item in recent_activity:
            item.pop("_ts", None)
        if not recent_activity:
            recent_activity = event_log[:20]

        connections = (
            db.query(PlatformConnectionModel)
            .filter(PlatformConnectionModel.streamer_id == streamer_id)
            .all()
        )
        connection_by_platform = {str(conn.platform or "").lower(): conn for conn in connections}
        streamer_settings = (streamer.settings_json or {}) if streamer else {}
        moderation_settings = streamer_settings.get("moderation") or {}
        voice_settings = streamer_settings.get("voice") or {}
        current_scene = obs_status.get("current_scene") or obs_status.get("scene")
        pre_stream_checks = [
            {
                "id": "obs",
                "label": "OBS connected",
                "passed": bool(obs_connected),
                "fix_label": "Check OBS →",
                "fix_href": "/setup",
            },
            {
                "id": "twitch",
                "label": "Twitch linked",
                "passed": bool(connection_by_platform.get("twitch") and connection_by_platform["twitch"].access_token),
                "fix_label": "Connect Twitch →",
                "fix_href": "/integrations",
            },
            {
                "id": "moderation",
                "label": "Moderation active",
                "passed": bool(moderation_settings.get("autoModerate", moderation_settings.get("enabled", True))),
                "fix_label": "Enable moderation",
                "fix_action": "enable_moderation",
            },
            {
                "id": "voice",
                "label": "Voice agent ready",
                "passed": bool(voice_settings.get("enabled", False)),
                "fix_label": "Set up voice →",
                "fix_href": "/voice",
            },
            {
                "id": "scene",
                "label": "Starting scene set",
                "passed": bool(current_scene and str(current_scene).strip().lower() not in {"unknown", "none"}),
                "fix_label": "Set scene in OBS →",
                "fix_href": "/",
            },
        ]
        pre_stream_ready = all(check.get("passed") for check in pre_stream_checks)

        return {
            "currentViewers": f"{current_viewers:,}",
            "viewerChange": viewer_change,
            "healthStatus": health_status,
            "healthScore": health_score,
            "streamPulse": {
                "score": pulse_score,
                "trend": pulse_trend,
                "label": _pulse_label(pulse_score),
                "chatPerMin": round(chat_5m / 5.0, 2),
                "engagementEvents10m": int(viewer_actions_10m),
            },
            "autoClips": auto_clips,
            "manualClips": manual_clips,
            "modEvents": int(mod_events),
            "autoModerated": auto_moderated,
            "currentScene": obs_status.get("current_scene") or obs_status.get("scene", "Unknown"),
            "obsConnected": obs_connected,
            "recording": bool(obs_status.get("recording", False)),
            "streaming": bool(obs_status.get("streaming", False)),
            "aiActive": bool(obs_connected or pending_commands > 0),
            "mlConfidence": ml_confidence,
            "userName": user_name or "Kazumi Streamer",
            "recentActivity": recent_activity[:20],
            "preStreamChecklist": {
                "ready": pre_stream_ready,
                "checks": pre_stream_checks,
            },
            "streamMetrics": {
                "cpuUsage": round(cpu_usage, 1),
                "memoryUsage": round(mem_usage, 1),
                "bitrateKbps": round(bitrate_kbps, 1),
                "droppedFrames": dropped_frames,
                "pendingCommands": int(pending_commands),
            },
        }
    finally:
        db.close()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = (websocket.query_params.get("token") or "").strip()
    user = None
    streamer_id = None
    if token:
        claims = verify_stream_access_token(token)
        if claims:
            user = get_user_by_id(int(claims["uid"]))
            streamer_id = int(claims["sid"])
        else:
            user = get_user_from_token(token)
            streamer_id = get_streamer_id_for_user(user) if user else None
    if not user:
        await websocket.close(code=1008)
        return
    await ws_manager.connect(websocket, streamer_id=streamer_id)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
            # You can handle incoming pings here if needed
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    token = (websocket.query_params.get("token") or "").strip()
    user = None
    if token:
        claims = verify_stream_access_token(token)
        if claims:
            user = get_user_by_id(int(claims["uid"]))
        else:
            user = get_user_from_token(token)
    if not user:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    while True:
        # This will send the PC Health data to your React Frontend
        data = await websocket.receive_text()
        await websocket.send_text(f"Message received: {data}")

@app.post("/api/mode/toggle")
async def toggle_streamer_mode(request: Request):
    """Toggle streamer mode on/off. When enabled, only streamer can access OBS commands."""
    _require_streamer_access(request)

    current_mode = getattr(request.app.state, 'streamer_mode', True)
    request.app.state.streamer_mode = not current_mode

    new_mode = request.app.state.streamer_mode
    status_msg = "enabled" if new_mode else "disabled"

    return {
        "status": "success",
        "streamer_mode": new_mode,
        "message": f"Streamer mode {status_msg}. {'Only streamer can control OBS.' if new_mode else 'Viewers can now interact freely.'}"
    }
@app.post("/system/restart")
async def restart_engine(request: Request):
    _require_streamer_access(request)
    try:
        import subprocess
        # This physically runs your .bat file from the frontend button
        subprocess.Popen(["start_kazumi.bat"], shell=True)
        return {"status": "success", "message": "Engine restarting..."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
    
