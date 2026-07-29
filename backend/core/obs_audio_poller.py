"""
Real-time OBS Audio Polling for Moment Detection

Continuously polls OBS audio input levels and sends them to the moment detector.
Works alongside chat events to trigger clip generation.
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class OBSAudioPoller:
    """Polls OBS audio levels and feeds them to moment detector"""

    def __init__(self, obs_adapter, detector, poll_interval_ms: int = 100):
        """
        Initialize OBS audio poller.

        Args:
            obs_adapter: OBS WebSocket adapter instance
            detector: MomentDetector instance
            poll_interval_ms: How often to poll OBS (milliseconds)
        """
        self.obs_adapter = obs_adapter
        self.detector = detector
        self.poll_interval_ms = poll_interval_ms / 1000.0
        self.running = False
        self._task: Optional[asyncio.Task] = None
        logger.info(f"OBS Audio Poller initialized (interval: {poll_interval_ms}ms)")

    async def start(self):
        """Start polling OBS audio levels"""
        if self.running:
            logger.warning("OBS Audio Poller already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("OBS Audio Poller started")

    async def stop(self):
        """Stop polling"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("OBS Audio Poller stopped")

    async def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                await self._poll_audio_level()
                await asyncio.sleep(self.poll_interval_ms)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Audio polling error: {e}")
                await asyncio.sleep(1)  # Back off on error

    async def _poll_audio_level(self):
        """Poll OBS for current audio levels and send to detector"""
        try:
            # Get stats from OBS which includes audio information
            stats = await self.obs_adapter.get_stats()

            if not stats or "error" in stats:
                return

            # OBS doesn't directly expose audio peak, so we estimate from bitrate/activity
            # When there's active audio, we'll see increased bitrate
            bitrate = stats.get("bitrate", 0)
            fps = stats.get("fps", 0)

            # Normalize audio peak: if streaming at reasonable FPS and bitrate, assume audio activity
            # This is a heuristic since OBS WebSocket doesn't expose raw audio levels
            if fps > 0 and bitrate > 500:  # Active stream
                # Map bitrate to audio peak (0.0-1.0)
                # Assume 2500-5000 kbps = audio active = 0.7-1.0 peak
                audio_peak = min(1.0, (bitrate - 500) / 5000.0)

                if audio_peak > 0.5:  # Only send significant peaks
                    self.detector.add_audio_peak(audio_peak, source="obs")
                    logger.debug(f"OBS audio peak: {audio_peak:.2f} (bitrate: {bitrate} kbps)")

        except Exception as e:
            logger.debug(f"Failed to poll OBS audio: {e}")


# Global poller instance
_audio_poller: Optional[OBSAudioPoller] = None


def get_audio_poller() -> Optional[OBSAudioPoller]:
    """Get the global OBS audio poller"""
    return _audio_poller


def set_audio_poller(poller: OBSAudioPoller):
    """Set the global OBS audio poller"""
    global _audio_poller
    _audio_poller = poller
