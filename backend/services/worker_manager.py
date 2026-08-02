import asyncio
import os
from typing import Dict, Optional
from datetime import datetime
import uuid

class ClipWorker:
    """Represents a single clip-generation worker for a live stream"""

    def __init__(self, channel_id: str, stream_id: str, stream_info: dict):
        self.worker_id = str(uuid.uuid4())[:8]
        self.channel_id = channel_id
        self.stream_id = stream_id
        self.stream_info = stream_info
        self.started_at = datetime.utcnow()
        self.is_running = True
        self.moments_detected = 0
        self.clips_generated = 0
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the worker loop"""
        print(f"🚀 Worker {self.worker_id} started for stream {self.stream_id}")
        self.task = asyncio.create_task(self._run())

    async def _run(self):
        """Main worker loop - would do actual clipping here"""
        try:
            while self.is_running:
                # TODO: Connect to stream data
                # TODO: Detect moments (chat + audio)
                # TODO: Generate clips
                # For now, just keep alive
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            print(f"🛑 Worker {self.worker_id} cancelled")
        except Exception as e:
            print(f"❌ Worker {self.worker_id} error: {e}")

    async def shutdown(self):
        """Graceful shutdown"""
        print(f"🛑 Shutting down worker {self.worker_id}")
        self.is_running = False

        # Finish any in-progress clips
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=10)
            except asyncio.TimeoutError:
                print(f"⚠️ Worker {self.worker_id} forced stop after timeout")
                self.task.cancel()

        duration = (datetime.utcnow() - self.started_at).total_seconds()
        print(f"✅ Worker {self.worker_id} stopped after {duration:.0f}s")
        print(f"   Moments detected: {self.moments_detected}")
        print(f"   Clips generated: {self.clips_generated}")

    def to_dict(self):
        """Serialize worker state"""
        duration = (datetime.utcnow() - self.started_at).total_seconds()
        return {
            "worker_id": self.worker_id,
            "channel_id": self.channel_id,
            "stream_id": self.stream_id,
            "stream_title": self.stream_info.get("title", "Unknown"),
            "started_at": self.started_at.isoformat(),
            "duration_seconds": duration,
            "is_running": self.is_running,
            "moments_detected": self.moments_detected,
            "clips_generated": self.clips_generated
        }


class WorkerManager:
    """Manages the pool of clip-generation workers"""

    def __init__(self):
        self.workers: Dict[str, ClipWorker] = {}  # channel_id -> worker
        self.max_concurrent = int(os.getenv("MAX_CONCURRENT_WORKERS", "20"))

    async def spawn_worker(self, channel_id: str, stream_id: str, stream_info: dict) -> ClipWorker:
        """Spawn a new worker for a stream"""
        if channel_id in self.workers:
            print(f"⚠️ Worker already exists for channel {channel_id}")
            return self.workers[channel_id]

        if len(self.workers) >= self.max_concurrent:
            print(f"❌ Max concurrent workers ({self.max_concurrent}) reached")
            return None

        worker = ClipWorker(channel_id, stream_id, stream_info)
        self.workers[channel_id] = worker
        await worker.start()

        print(f"📊 Active workers: {len(self.workers)}/{self.max_concurrent}")
        return worker

    async def shutdown_worker(self, channel_id: str):
        """Shutdown a worker"""
        if channel_id not in self.workers:
            print(f"⚠️ No worker found for channel {channel_id}")
            return

        worker = self.workers[channel_id]
        await worker.shutdown()
        del self.workers[channel_id]

        print(f"📊 Active workers: {len(self.workers)}/{self.max_concurrent}")

    def get_worker(self, channel_id: str) -> Optional[ClipWorker]:
        """Get a running worker"""
        return self.workers.get(channel_id)

    def get_all_workers(self) -> Dict[str, dict]:
        """Get all running workers as dicts"""
        return {
            channel_id: worker.to_dict()
            for channel_id, worker in self.workers.items()
        }

    async def shutdown_all(self):
        """Shutdown all workers"""
        print(f"🛑 Shutting down {len(self.workers)} workers...")
        for channel_id in list(self.workers.keys()):
            await self.shutdown_worker(channel_id)


# Global instance
_manager: Optional[WorkerManager] = None

def get_worker_manager() -> WorkerManager:
    global _manager
    if _manager is None:
        _manager = WorkerManager()
    return _manager
