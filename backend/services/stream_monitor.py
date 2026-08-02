import asyncio
import os
import json
from typing import Optional, Dict, Set
from datetime import datetime
from backend.integrations.youtube import get_youtube_client
from backend.services.worker_manager import get_worker_manager

# Track active streams to avoid duplicate spawns
ACTIVE_STREAMS: Dict[str, dict] = {}

class StreamMonitor:
    def __init__(self):
        self.youtube_client = get_youtube_client()
        self.worker_manager = get_worker_manager()
        self.check_interval = int(os.getenv("STREAM_MONITOR_INTERVAL", "30"))  # seconds
        self.running = False

    async def start(self):
        """Start monitoring streams"""
        self.running = True
        print("🔍 Stream Monitor Started")
        await self._monitor_loop()

    async def stop(self):
        """Stop monitoring"""
        self.running = False
        print("🛑 Stream Monitor Stopped")

    async def _monitor_loop(self):
        """Main monitoring loop - runs every N seconds"""
        while self.running:
            try:
                await self._check_all_streams()
            except Exception as e:
                print(f"❌ Monitor error: {e}")

            await asyncio.sleep(self.check_interval)

    async def _check_all_streams(self):
        """Check all registered streamers"""
        # For MVP, we'll check hardcoded channel ID
        # Later, this will query the database for all streamers

        youtube_channel_id = os.getenv("YOUTUBE_CHANNEL_ID")
        if not youtube_channel_id:
            print("⚠️ YOUTUBE_CHANNEL_ID not set in env")
            return

        is_live = await self.youtube_client.is_channel_live(youtube_channel_id)

        if is_live and youtube_channel_id not in ACTIVE_STREAMS:
            # Stream just went live
            stream_info = await self.youtube_client.get_live_stream_info(youtube_channel_id)
            await self._on_stream_started(youtube_channel_id, stream_info)

        elif not is_live and youtube_channel_id in ACTIVE_STREAMS:
            # Stream just ended
            await self._on_stream_ended(youtube_channel_id)

    async def _on_stream_started(self, channel_id: str, stream_info: Optional[dict]):
        """Called when a stream goes live"""
        ACTIVE_STREAMS[channel_id] = {
            "started_at": datetime.utcnow().isoformat(),
            "video_id": stream_info.get("video_id") if stream_info else None,
            "title": stream_info.get("title") if stream_info else "Unknown"
        }

        print(f"✅ STREAM STARTED: {channel_id}")
        print(f"   Title: {ACTIVE_STREAMS[channel_id]['title']}")
        print(f"   Video ID: {ACTIVE_STREAMS[channel_id]['video_id']}")

        # Spawn clip worker
        stream_id = stream_info.get("video_id") if stream_info else channel_id
        await self.worker_manager.spawn_worker(channel_id, stream_id, stream_info or {})

    async def _on_stream_ended(self, channel_id: str):
        """Called when a stream ends"""
        if channel_id in ACTIVE_STREAMS:
            started = ACTIVE_STREAMS[channel_id]["started_at"]
            print(f"🛑 STREAM ENDED: {channel_id}")
            print(f"   Duration: started at {started}")

            del ACTIVE_STREAMS[channel_id]

        # Shutdown clip worker
        await self.worker_manager.shutdown_worker(channel_id)

    @staticmethod
    def get_active_streams() -> Dict[str, dict]:
        """Get currently active streams"""
        return ACTIVE_STREAMS.copy()

# Global instance
_monitor: Optional[StreamMonitor] = None

def get_stream_monitor() -> StreamMonitor:
    global _monitor
    if _monitor is None:
        _monitor = StreamMonitor()
    return _monitor

async def start_stream_monitor():
    """Start the stream monitor (call this from main.py)"""
    monitor = get_stream_monitor()
    asyncio.create_task(monitor.start())

def get_active_streams() -> Dict[str, dict]:
    """Get active streams"""
    return StreamMonitor.get_active_streams()
