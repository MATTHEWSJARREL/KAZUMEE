from fastapi import APIRouter, Request, HTTPException
from backend.services.stream_monitor import get_active_streams, get_stream_monitor
from backend.services.worker_manager import get_worker_manager

router = APIRouter(prefix="/api/streams", tags=["streams"])

@router.get("/active")
async def get_active_streams_endpoint(request: Request):
    """Get currently active streams being monitored"""
    try:
        active = get_active_streams()
        return {
            "active_streams": active,
            "count": len(active),
            "status": "ok"
        }
    except Exception as e:
        return {
            "active_streams": {},
            "count": 0,
            "status": "error",
            "error": str(e)
        }

@router.get("/workers")
async def get_workers_endpoint(request: Request):
    """Get all active clip-generation workers"""
    try:
        manager = get_worker_manager()
        workers = manager.get_all_workers()
        return {
            "workers": workers,
            "active_count": len(workers),
            "max_concurrent": manager.max_concurrent,
            "status": "ok"
        }
    except Exception as e:
        return {
            "workers": {},
            "active_count": 0,
            "status": "error",
            "error": str(e)
        }

@router.post("/test/stream-start")
async def test_stream_start(channel_id: str = "test_channel_1", title: str = "Test Stream"):
    """
    TESTING ONLY: Simulate a stream starting
    This triggers worker spawn WITHOUT needing a real YouTube stream
    """
    try:
        monitor = get_stream_monitor()
        stream_info = {
            "video_id": f"test_video_{channel_id}",
            "title": title,
            "channel_id": channel_id,
            "is_live": True
        }
        await monitor._on_stream_started(channel_id, stream_info)
        return {
            "status": "ok",
            "message": f"Stream started: {title}",
            "channel_id": channel_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/stream-end")
async def test_stream_end(channel_id: str = "test_channel_1"):
    """
    TESTING ONLY: Simulate a stream ending
    This triggers worker shutdown WITHOUT needing a real YouTube stream
    """
    try:
        monitor = get_stream_monitor()
        await monitor._on_stream_ended(channel_id)
        return {
            "status": "ok",
            "message": f"Stream ended: {channel_id}",
            "channel_id": channel_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/moment")
async def test_moment(
    channel_id: str = "test_1",
    chat_velocity: float = 8.5,
    audio_peak: float = 0.85
):
    """
    TESTING ONLY: Simulate a moment being detected
    This broadcasts to active workers WITHOUT needing real chat/audio data
    """
    try:
        manager = get_worker_manager()

        moment_data = {
            "moment_id": f"test_moment_{int(__import__('time').time() * 1000)}",
            "timestamp": __import__('time').time(),
            "chat_velocity": chat_velocity,
            "audio_peak": audio_peak,
            "combined_score": (chat_velocity / 5.0 * 50) + (audio_peak / 0.6 * 50),
            "context": f"TEST: Chat spike ({chat_velocity:.1f} msg/s) + Audio peak ({audio_peak:.2f})"
        }

        await manager.broadcast_moment(moment_data, channel_id=channel_id)

        worker = manager.get_worker(channel_id)
        if not worker:
            return {
                "status": "warning",
                "message": f"No active worker for channel {channel_id}",
                "channel_id": channel_id
            }

        return {
            "status": "ok",
            "message": f"Moment broadcast to worker {worker.worker_id}",
            "channel_id": channel_id,
            "worker_id": worker.worker_id,
            "moment_data": moment_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
