"""
Moment Detection API Routes

Receives real-time chat and audio events, feeds them to the detector,
and auto-triggers clip generation when moments are detected.
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, WebSocket, Depends
from pydantic import BaseModel
import logging
from typing import Optional
import json
import asyncio
from backend.core.moment_detector import DetectedMoment
from backend.core.auth import get_current_user, get_streamer_id_for_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/moments", tags=["MomentDetection"])


# ==============================================================================
# MOMENT-TO-AGENT BRIDGE
# ==============================================================================

async def on_moment_detected_send_clip_command(moment: DetectedMoment):
    """
    Callback: When moment is detected, send clip command to ONLY that streamer's agent.
    CRITICAL: targeted send, not broadcast — prevents cross-account clip commands.
    """
    try:
        from backend.api.routes.agent import send_clip_command_to_agent, connected_agents

        streamer_id = moment.streamer_id
        all_connected = list(connected_agents.keys())

        logger.info(f"[MOMENT→AGENT] Moment detected for streamer {streamer_id} | "
                   f"Score: {moment.combined_score}/100 | Connected agents: {all_connected}")

        success = await send_clip_command_to_agent(streamer_id)

        if success:
            logger.info(f"[MOMENT→AGENT] ✅ Clip command sent to streamer {streamer_id}")
        else:
            logger.warning(f"[MOMENT→AGENT] ❌ Agent offline for streamer {streamer_id}")

    except Exception as e:
        logger.error(f"[MOMENT→AGENT] ❌ Failed to send clip command to agent: {e}")


# ==============================================================================
# REGISTER CALLBACK ON STARTUP
# ==============================================================================

_callback_registered = False

def _register_agent_callback():
    """Register the agent callback with the detector (called once on startup)"""
    global _callback_registered
    if _callback_registered:
        return

    try:
        from backend.core.moment_detector import get_detector
        detector = get_detector()
        detector.on_moment_detected(on_moment_detected_send_clip_command)
        _callback_registered = True
        logger.info("[AGENT BRIDGE] Registered moment → clip-command callback")
    except Exception as e:
        logger.error(f"Failed to register agent callback: {e}")

# Register on first API call
def ensure_agent_callback_registered():
    """Ensure callback is registered (call this at the start of each endpoint)"""
    _register_agent_callback()


class ChatEventRequest(BaseModel):
    """Chat message event from Twitch/YouTube/etc"""
    source: str  # "twitch" | "youtube" | "kick" | etc
    username: str
    message: str
    timestamp: Optional[float] = None


class AudioEventRequest(BaseModel):
    """Audio peak event from system audio"""
    peak_value: float  # 0.0-1.0
    source: str  # "obs" | "system" | etc
    timestamp: Optional[float] = None


@router.post("/chat-event")
async def on_chat_event(
    request: Request,
    payload: ChatEventRequest,
    current_user = Depends(get_current_user)
):
    """Register a chat message for moment detection (scoped to authenticated streamer)."""
    ensure_agent_callback_registered()

    # Get streamer_id from authenticated user - REQUIRED
    streamer_id = get_streamer_id_for_user(current_user)
    if not streamer_id:
        logger.warning(f"Chat event rejected: no streamer_id for user {current_user.id if current_user else 'anonymous'}")
        raise HTTPException(status_code=400, detail="Chat event must be tied to a streamer")

    try:
        from backend.core.moment_detector import get_detector
        detector = get_detector()
        detector.add_chat_message(
            streamer_id=streamer_id,
            source=payload.source,
            message=payload.message
        )

        return {
            "status": "ok",
            "message": f"Chat from {payload.source} recorded for streamer {streamer_id}",
        }

    except Exception as e:
        logger.error(f"Failed to process chat event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio-event")
async def on_audio_event(
    request: Request,
    payload: AudioEventRequest,
    current_user = Depends(get_current_user)
):
    """Register an audio peak for moment detection (scoped to authenticated streamer)."""
    ensure_agent_callback_registered()

    # Get streamer_id from authenticated user - REQUIRED
    streamer_id = get_streamer_id_for_user(current_user)
    if not streamer_id:
        logger.warning(f"Audio event rejected: no streamer_id for user {current_user.id if current_user else 'anonymous'}")
        raise HTTPException(status_code=400, detail="Audio event must be tied to a streamer")

    try:
        from backend.core.moment_detector import get_detector
        detector = get_detector()
        detector.add_audio_peak(
            streamer_id=streamer_id,
            peak_value=payload.peak_value,
            source=payload.source
        )

        return {
            "status": "ok",
            "audio_peak": payload.peak_value,
            "streamer_id": streamer_id,
        }

    except Exception as e:
        logger.error(f"Failed to process audio event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def detector_status():
    """Get real-time detector status."""
    from backend.core.moment_detector import get_detector
    detector = get_detector()
    status = detector.get_status()

    return {
        "status": "ok",
        "detector": status,
        "callbacks_registered": len(detector._callbacks),  # Debug: show how many callbacks
    }

@router.get("/debug/callbacks")
async def debug_callbacks():
    """Debug endpoint: show what callbacks are registered"""
    from backend.core.moment_detector import get_detector
    detector = get_detector()

    callback_names = []
    for cb in detector._callbacks:
        callback_names.append({
            "function": cb.__name__ if hasattr(cb, '__name__') else str(type(cb)),
            "is_coroutine": "async" if asyncio.iscoroutinefunction(cb) else "sync"
        })

    return {
        "total_callbacks": len(detector._callbacks),
        "callbacks": callback_names,
    }


@router.post("/test")
async def test_moment_detection(background_tasks: BackgroundTasks, streamer_id: int = 1):
    """Simulate a moment detection for testing (defaults to streamer 1)."""
    ensure_agent_callback_registered()
    try:
        from backend.core.moment_detector import get_detector
        detector = get_detector()

        # Simulate realistic chat spike with hype indicators
        hype_messages = ["PogChamp", "OMEGALUL", "clip it", "insane", "no way", "WHAT", "W W W", "hype hype", "!!!"]
        for i in range(15):
            msg = hype_messages[i % len(hype_messages)]
            detector.add_chat_message(streamer_id=streamer_id, source="test", message=msg)

        # Simulate audio spike
        detector.add_audio_peak(streamer_id=streamer_id, peak_value=0.75, source="test")

        return {
            "status": "test_moment_sent",
            "message": "Simulated realistic hype moment (15 messages + audio)",
        }

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_detector():
    """Reset detector buffers for new stream"""
    try:
        from backend.core.moment_detector import get_detector
        detector = get_detector()
        detector.reset()

        return {
            "status": "ok",
            "message": "Detector reset for new stream",
        }

    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def wire_detector_to_clip_generator():
    """Set up the detector callback to trigger real clip generation."""
    from backend.core.moment_detector import get_detector
    from backend.core.clip_generator_service import ClipGeneratorService
    from backend.commands.obs_adapter import obs_bridge

    detector = get_detector()

    # Lazy initialize clip generator
    try:
        clip_gen = ClipGeneratorService(obs_adapter=obs_bridge)
        detector.on_moment_detected(clip_gen.on_moment_detected)
        logger.info("✅ Detector wired to Clip Generator Service (with video extraction)")
    except Exception as e:
        logger.warning(f"Clip generator initialization failed: {e}, using fallback")
        return wire_detector_to_auto_clip_fallback()


def wire_detector_to_auto_clip_fallback():
    """Fallback: simple DB insert (for when clip generator not available)"""
    from backend.core.moment_detector import get_detector, DetectedMoment

    detector = get_detector()

    async def on_moment_callback(moment: DetectedMoment):
        """Fallback: create pending clip entry in DB"""
        logger.info(f"🎬 Auto-clipping moment (fallback): {moment.moment_id}")

        title_map = {
            (80, 100): "EPIC MOMENT",
            (60, 80): "HIGHLIGHT",
            (40, 60): "INTERESTING MOMENT",
            (0, 40): "MOMENT DETECTED",
        }

        title = "MOMENT DETECTED"
        for (low, high), title_text in title_map.items():
            if low <= moment.combined_score < high:
                title = title_text
                break

        db_session = None
        try:
            from backend.database.session import SessionLocal
            from sqlalchemy import text

            db_session = SessionLocal()
            db_session.execute(text("""
                INSERT INTO clips (
                    title, description, file_path, status,
                    requested_by_type, requested_by_name,
                    duration_seconds, quality_score,
                    stream_session_id, streamer_id
                ) VALUES (
                    :title, :description, :file_path, :status,
                    :requested_by_type, :requested_by_name,
                    :duration_seconds, :quality_score,
                    :stream_session_id, :streamer_id
                )
            """), {
                "title": title,
                "description": moment.context,
                "file_path": f"pending_auto_clip_{moment.moment_id}.mp4",
                "status": "pending",
                "requested_by_type": "auto_detection",
                "requested_by_name": "Kazumee AI",
                "duration_seconds": 45,
                "quality_score": min(moment.combined_score / 100, 1.0),
                "stream_session_id": 1,
                "streamer_id": 1
            })
            db_session.commit()
            logger.info(f"✅ Auto-clip created (fallback): {title}")
        except Exception as e:
            logger.error(f"❌ Fallback clip creation failed: {e}")
            if db_session:
                db_session.rollback()
        finally:
            if db_session:
                db_session.close()

    detector.on_moment_detected(on_moment_callback)
    logger.info("✅ Detector wired to fallback auto-clip system")


# NOTE: Wiring happens in backend/main.py lifespan after ClipGeneratorService is initialized


# Global WebSocket manager for moment updates
_websocket_clients = []


@router.websocket("/ws/updates")
async def websocket_moment_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time moment detection updates."""
    await websocket.accept()
    _websocket_clients.append(websocket)
    logger.info(f"✅ WebSocket client connected. Total: {len(_websocket_clients)}")

    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "message": "Connected to moment detection service"
        }))

        while True:
            try:
                # Wait for messages with a timeout to allow heartbeat
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    logger.debug("WebSocket ping/pong")
            except asyncio.TimeoutError:
                # Send periodic status update as heartbeat
                try:
                    from backend.core.moment_detector import get_detector
                    detector = get_detector()
                    status = detector.get_status()
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat",
                        "detector_status": status
                    }))
                except Exception as e:
                    logger.warning(f"Failed to send heartbeat: {e}")

    except Exception as e:
        logger.warning(f"❌ WebSocket error: {e}")
    finally:
        if websocket in _websocket_clients:
            _websocket_clients.remove(websocket)
        logger.info(f"⏸️  WebSocket client disconnected. Total: {len(_websocket_clients)}")


async def broadcast_moment_update(update_data):
    """Broadcast moment detection update to all connected WebSocket clients."""
    message = json.dumps({
        "type": "moment_update",
        "data": update_data
    })

    disconnected = []
    for client in _websocket_clients:
        try:
            await client.send_text(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket update: {e}")
            disconnected.append(client)

    # Clean up disconnected clients
    for client in disconnected:
        if client in _websocket_clients:
            _websocket_clients.remove(client)


def wire_detector_to_websocket():
    """Wire moment detector to broadcast via WebSocket."""
    from backend.core.moment_detector import get_detector, DetectedMoment
    import asyncio

    detector = get_detector()

    async def on_websocket_callback(moment: DetectedMoment):
        """Broadcast moment detection via WebSocket."""
        try:
            await broadcast_moment_update({
                "moment_id": moment.moment_id,
                "combined_score": moment.combined_score,
                "context": moment.context,
                "timestamp": moment.timestamp.isoformat() if hasattr(moment.timestamp, 'isoformat') else str(moment.timestamp),
            })
            logger.info(f"WebSocket broadcast for moment: {moment.moment_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast moment via WebSocket: {e}")

    detector.on_moment_detected(on_websocket_callback)
    logger.info("Detector wired to WebSocket broadcasting")


# Wire WebSocket broadcasting on module import
try:
    wire_detector_to_websocket()
except Exception as e:
    logger.warning(f"Failed to wire WebSocket: {e}")
