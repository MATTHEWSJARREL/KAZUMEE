"""Real-Time Moment Detection for Auto-Clipping"""

import logging
import time
import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)


@dataclass
class DetectedMoment:
    """A moment has been detected - ready to clip"""
    moment_id: str
    timestamp: float
    chat_velocity: float
    audio_peak: float
    combined_score: float
    context: str


class MomentDetector:
    """Detects interesting moments by combining chat velocity + audio peaks."""

    def __init__(self, window_size: float = 2.0, sensitivity: float = 0.7):
        self.window_size = window_size
        self.sensitivity = sensitivity

        self.chat_window: deque = deque()
        self.audio_peaks: deque = deque()

        self.last_moment_time = 0.0
        self.debounce_interval = 30.0

        self._callbacks: List[Callable[[DetectedMoment], None]] = []

    def on_moment_detected(self, callback: Callable[[DetectedMoment], None]):
        """Register callback for when a moment is detected"""
        self._callbacks.append(callback)

    def add_chat_message(self, source: str = "twitch"):
        """Register a chat message"""
        current_time = time.time()

        # Clean old windows
        while self.chat_window and (current_time - self.chat_window[0][0]) > self.window_size:
            self.chat_window.popleft()

        # Add to current window
        if self.chat_window and (current_time - self.chat_window[-1][0]) < 0.1:
            self.chat_window[-1] = (self.chat_window[-1][0], self.chat_window[-1][1] + 1)
        else:
            self.chat_window.append((current_time, 1))

        self._check_moment_triggered(source)

    def add_audio_peak(self, peak_value: float, source: str = "obs"):
        """Register an audio peak (0.0-1.0)"""
        current_time = time.time()

        # Clean old peaks
        while self.audio_peaks and (current_time - self.audio_peaks[0][0]) > self.window_size:
            self.audio_peaks.popleft()

        # Add this peak
        if peak_value > 0.5:
            self.audio_peaks.append((current_time, peak_value))

        self._check_moment_triggered(source)

    def _get_chat_velocity(self) -> float:
        """Get current chat messages per second"""
        if not self.chat_window:
            return 0.0

        total_messages = sum(count for _, count in self.chat_window)
        elapsed = time.time() - self.chat_window[0][0]

        # For rapid bursts, estimate velocity from message count
        if elapsed < 0.05:
            return float(total_messages)  # Raw count for quick bursts

        if elapsed < 0.1:
            return 1.0

        return total_messages / elapsed

    def _get_audio_peak(self) -> float:
        """Get max audio peak in current window"""
        if not self.audio_peaks:
            return 0.0

        return max(peak for _, peak in self.audio_peaks)

    def _check_moment_triggered(self, source: str):
        """Check if current signal combination triggers a moment"""
        current_time = time.time()
        if (current_time - self.last_moment_time) < self.debounce_interval:
            return

        chat_vel = self._get_chat_velocity()
        audio_peak = self._get_audio_peak()

        chat_threshold = 5.0 * (1.0 - self.sensitivity)
        audio_threshold = 0.6 * (1.0 - self.sensitivity)

        chat_triggered = chat_vel > chat_threshold
        audio_triggered = audio_peak > audio_threshold

        if chat_triggered and audio_triggered:
            self.last_moment_time = current_time

            chat_score = min(100, (chat_vel / chat_threshold) * 50)
            audio_score = min(100, (audio_peak / audio_threshold) * 50)
            combined_score = chat_score + audio_score

            moment = DetectedMoment(
                moment_id=f"moment_{int(current_time * 1000)}",
                timestamp=current_time,
                chat_velocity=chat_vel,
                audio_peak=audio_peak,
                combined_score=combined_score,
                context=f"Chat spike ({chat_vel:.1f} msg/s) + Audio peak ({audio_peak:.2f})",
            )

            logger.info(f"[MOMENT] DETECTED: {moment.context} (score: {combined_score:.0f}/100)")

            for callback in self._callbacks:
                try:
                    # Handle both sync and async callbacks
                    if asyncio.iscoroutinefunction(callback):
                        # For async callbacks, run in background task
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(callback(moment))
                        except RuntimeError:
                            # No event loop, use run_until_complete
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(callback(moment))
                    else:
                        # Sync callback
                        callback(moment)
                except Exception as e:
                    logger.error(f"Moment callback failed: {e}")

    def set_sensitivity(self, sensitivity: float):
        """Update detection sensitivity (0.0-1.0)"""
        self.sensitivity = max(0.0, min(1.0, float(sensitivity)))
        logger.info(f"Detector sensitivity updated to {self.sensitivity:.2f}")

    def get_status(self) -> dict:
        """Get current detector status"""
        return {
            "chat_velocity": self._get_chat_velocity(),
            "audio_peak": self._get_audio_peak(),
            "active_chat_windows": len(self.chat_window),
            "active_audio_peaks": len(self.audio_peaks),
            "time_since_last_moment": time.time() - self.last_moment_time,
            "sensitivity": self.sensitivity,
        }

    def reset(self):
        """Clear all buffers"""
        self.chat_window.clear()
        self.audio_peaks.clear()
        self.last_moment_time = 0.0
        logger.info("Moment detector reset")


_detector: Optional[MomentDetector] = None


def get_detector() -> MomentDetector:
    """Get or create the global moment detector"""
    global _detector
    if _detector is None:
        _detector = MomentDetector(window_size=2.0, sensitivity=0.7)
        logger.info("Moment detector initialized (sensitivity=0.7)")
    return _detector
