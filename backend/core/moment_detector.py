"""Real-Time Moment Detection for Auto-Clipping - Approach 2: Adaptive Z-Score"""

import logging
import time
import asyncio
import re
from collections import deque
from dataclasses import dataclass
from typing import Optional, Callable, List
import math

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
    streamer_id: int  # CRITICAL: which streamer's stream detected this moment


class MomentDetector:
    """Detects moments using adaptive z-score, rate-of-change, and cheap signals."""

    def __init__(self, window_size: float = 2.0, sensitivity: float = 0.7):
        self.window_size = window_size
        self.sensitivity = sensitivity

        # EWMA state for chat (exponentially-weighted moving average)
        self.chat_ewma_mean = 0.5  # baseline messages/sec
        self.chat_ewma_var = 0.1   # baseline variance
        self.chat_ewma_alpha = 0.15  # decay factor (0.15 = weight last update 15%, slow adaptation)
        self.chat_prev_velocity = 0.0
        self.chat_message_count = 0
        self.chat_last_bucket_time = time.time()

        # EWMA state for audio
        self.audio_ewma_mean = 0.1  # baseline peak
        self.audio_ewma_var = 0.02  # baseline variance
        self.audio_ewma_alpha = 0.15  # slower adaptation prevents baseline creep
        self.audio_prev_peak = 0.0

        # Message history for cheap signal extraction (last 50 messages)
        self.message_history: deque = deque(maxlen=50)

        # Baseline freeze during active moments
        self.active_moment_time = 0.0
        self.active_moment_freeze_duration = 10.0  # seconds

        self.last_moment_time = 0.0
        self.debounce_interval = 30.0

        self.start_time = time.time()  # For cold-start handling
        self.cold_start_duration = 60.0  # seconds

        self._callbacks: List[Callable[[DetectedMoment], None]] = []

        # Hype score weights (sum to 1.0)
        self.weight_chat_zscore = 0.30
        self.weight_audio_zscore = 0.20
        self.weight_acceleration = 0.20
        self.weight_emote_density = 0.30  # Increase weight on cheap signals (they're most reliable)
        self.hype_threshold = 0.50  # 0-1 scale (reasonable for production)
        self.chat_zscore_floor = 0.3  # soft floor, allow moments even with modest chat

    def on_moment_detected(self, callback: Callable[[DetectedMoment], None]):
        """Register callback for when a moment is detected"""
        self._callbacks.append(callback)

    def add_chat_message(self, source: str = "twitch", message: str = "", streamer_id: int):
        """Register a chat message (now extracts signals too)"""
        current_time = time.time()

        # Update chat velocity via bucket counting (still 2-second window for velocity)
        time_since_bucket = current_time - self.chat_last_bucket_time
        if time_since_bucket >= self.window_size:
            # Bucket complete: compute velocity and update EWMA
            if time_since_bucket > 0:
                current_velocity = self.chat_message_count / time_since_bucket
            else:
                current_velocity = 0.0

            self._update_chat_ewma(current_velocity)
            self.chat_message_count = 1  # Start new bucket
            self.chat_last_bucket_time = current_time
        else:
            self.chat_message_count += 1

        # Store message for cheap signal extraction
        self.message_history.append({
            "timestamp": current_time,
            "message": message.lower() if message else "",
            "source": source
        })

        self._check_moment_triggered(source, streamer_id)

    def add_audio_peak(self, peak_value: float, source: str = "obs", streamer_id: int):
        """Register an audio peak (0.0-1.0)"""
        current_time = time.time()

        # Update audio EWMA
        self._update_audio_ewma(peak_value)

        self._check_moment_triggered(source, streamer_id)

    def _update_chat_ewma(self, current_velocity: float):
        """Update exponentially-weighted moving average for chat velocity"""
        # Freeze baseline during active moment
        if self._is_baseline_frozen():
            return

        # EWMA update: new_mean = α·x + (1-α)·old_mean
        prev_mean = self.chat_ewma_mean
        self.chat_ewma_mean = self.chat_ewma_alpha * current_velocity + (1 - self.chat_ewma_alpha) * self.chat_ewma_mean

        # Update variance using squared deviations
        deviation = current_velocity - prev_mean
        self.chat_ewma_var = self.chat_ewma_alpha * (deviation ** 2) + (1 - self.chat_ewma_alpha) * self.chat_ewma_var

        self.chat_prev_velocity = current_velocity

    def _update_audio_ewma(self, current_peak: float):
        """Update exponentially-weighted moving average for audio peak"""
        # Freeze baseline during active moment
        if self._is_baseline_frozen():
            return

        prev_mean = self.audio_ewma_mean
        self.audio_ewma_mean = self.audio_ewma_alpha * current_peak + (1 - self.audio_ewma_alpha) * self.audio_ewma_mean

        # Update variance
        deviation = current_peak - prev_mean
        self.audio_ewma_var = self.audio_ewma_alpha * (deviation ** 2) + (1 - self.audio_ewma_alpha) * self.audio_ewma_var

        self.audio_prev_peak = current_peak

    def _is_baseline_frozen(self) -> bool:
        """Check if we're currently in an active moment (baseline should be frozen)"""
        current_time = time.time()
        return (current_time - self.active_moment_time) < self.active_moment_freeze_duration

    def _get_chat_velocity(self) -> float:
        """Get current chat velocity (from EWMA mean)"""
        return self.chat_ewma_mean

    def _get_audio_peak(self) -> float:
        """Get current audio baseline (from EWMA mean)"""
        return self.audio_ewma_mean

    def _compute_zscore(self, value: float, mean: float, variance: float) -> float:
        """Compute z-score: (value - mean) / sqrt(variance)"""
        if variance <= 0:
            return 0.0
        std = math.sqrt(variance)
        if std == 0:
            return 0.0
        return (value - mean) / std

    def _get_emote_and_keyword_signals(self) -> tuple:
        """Extract cheap signals: emote density, keyword presence, duplicate ratio"""
        if not self.message_history:
            return 0.0, 0, 0.0

        # Common emotes and hype indicators
        hype_emotes = {"lul", "omegalul", "pogchamp", "pog", "hype", "clap", "w", "ez", "gg"}
        hype_keywords = {"clip", "clip it", "clip that", "moment", "insane", "what", "no way"}

        recent_messages = list(self.message_history)[-20:]  # Last 20 messages
        emote_count = 0
        keyword_count = 0
        unique_messages = set()
        all_messages = []

        for msg_data in recent_messages:
            msg = msg_data["message"]
            all_messages.append(msg)
            unique_messages.add(msg)

            # Check for hype emotes
            for emote in hype_emotes:
                if emote in msg:
                    emote_count += 1
                    break

            # Check for keywords
            for keyword in hype_keywords:
                if keyword in msg:
                    keyword_count += 1
                    break

        emote_density = emote_count / len(recent_messages) if recent_messages else 0.0
        duplicate_ratio = 1.0 - (len(unique_messages) / len(all_messages)) if all_messages else 0.0

        return emote_density, keyword_count, duplicate_ratio

    def _check_moment_triggered(self, source: str, streamer_id: int):
        """Check if current signal combination triggers a moment (weighted z-score approach)"""
        current_time = time.time()
        if (current_time - self.last_moment_time) < self.debounce_interval:
            return

        # Cold-start handling: use conservative threshold for first 60 seconds
        elapsed_since_start = current_time - self.start_time
        in_cold_start = elapsed_since_start < self.cold_start_duration

        # Get current signals
        chat_vel = self.chat_prev_velocity if self.chat_prev_velocity > 0 else self.chat_ewma_mean
        audio_peak = self.audio_prev_peak if self.audio_prev_peak > 0 else self.audio_ewma_mean

        # Compute z-scores (how far above/below baseline)
        chat_zscore = self._compute_zscore(chat_vel, self.chat_ewma_mean, self.chat_ewma_var)
        audio_zscore = self._compute_zscore(audio_peak, self.audio_ewma_mean, self.audio_ewma_var)

        # Rate of change (acceleration)
        if self.chat_prev_velocity > 0 and self.chat_ewma_mean > 0:
            chat_accel = (self.chat_prev_velocity - self.chat_ewma_mean) / max(self.chat_ewma_mean, 0.1)
        else:
            chat_accel = 0.0

        # Cheap signals (emote density, keywords, duplicates)
        emote_density, keyword_count, duplicate_ratio = self._get_emote_and_keyword_signals()

        # Emote density z-score (expect ~5% emotes normally, spike to 30%+)
        baseline_emote_density = 0.05
        emote_zscore = self._compute_zscore(emote_density, baseline_emote_density, 0.01)

        # Normalize z-scores to 0-1 scale (clip at ±3 sigma)
        def normalize_zscore(z: float) -> float:
            return max(0.0, min(1.0, (z + 3.0) / 6.0))

        chat_score = normalize_zscore(chat_zscore)
        audio_score = normalize_zscore(audio_zscore)
        accel_score = normalize_zscore(chat_accel)
        emote_score = normalize_zscore(emote_zscore)

        # Soft floor: require some chat engagement
        if chat_score < self.chat_zscore_floor and not (keyword_count > 0 or duplicate_ratio > 0.4):
            return

        # Weighted hype score
        hype_score = (
            self.weight_chat_zscore * chat_score +
            self.weight_audio_zscore * audio_score +
            self.weight_acceleration * accel_score +
            self.weight_emote_density * emote_score
        )

        # Cold-start uses slightly higher threshold (1.15x) to avoid false positives during setup
        threshold = self.hype_threshold * 1.15 if in_cold_start else self.hype_threshold

        if hype_score > threshold:
            self.last_moment_time = current_time
            self.active_moment_time = current_time  # Freeze baseline

            combined_score = int(hype_score * 100)
            context = f"Hype detected: chat_z={chat_zscore:.1f}, audio_z={audio_zscore:.1f}, accel={chat_accel:.1f}, emotes={emote_density:.0%}"

            moment = DetectedMoment(
                moment_id=f"moment_{int(current_time * 1000)}",
                timestamp=current_time,
                chat_velocity=chat_vel,
                audio_peak=audio_peak,
                combined_score=combined_score,
                context=context,
                streamer_id=streamer_id,
            )

            logger.info(f"[MOMENT] DETECTED: score={combined_score}/100 | {context}")

            for callback in self._callbacks:
                try:
                    # Handle both sync and async callbacks
                    if asyncio.iscoroutinefunction(callback):
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(callback(moment))
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(callback(moment))
                    else:
                        callback(moment)
                except Exception as e:
                    logger.error(f"Moment callback failed: {e}")

    def set_sensitivity(self, sensitivity: float):
        """Update detection sensitivity (0.0-1.0)"""
        self.sensitivity = max(0.0, min(1.0, float(sensitivity)))
        # Adjust threshold based on sensitivity - now 0.40-0.55 range for better detection
        self.hype_threshold = 0.40 + (1.0 - sensitivity) * 0.15
        logger.info(f"Detector sensitivity updated to {self.sensitivity:.2f}, threshold={self.hype_threshold:.2f}")

    def get_status(self) -> dict:
        """Get current detector status"""
        emote_density, keyword_count, duplicate_ratio = self._get_emote_and_keyword_signals()
        chat_zscore = self._compute_zscore(self.chat_prev_velocity, self.chat_ewma_mean, self.chat_ewma_var)
        audio_zscore = self._compute_zscore(self.audio_prev_peak, self.audio_ewma_mean, self.audio_ewma_var)

        return {
            "chat_velocity": self._get_chat_velocity(),
            "chat_baseline": self.chat_ewma_mean,
            "chat_zscore": chat_zscore,
            "audio_peak": self._get_audio_peak(),
            "audio_baseline": self.audio_ewma_mean,
            "audio_zscore": audio_zscore,
            "emote_density": emote_density,
            "keyword_count": keyword_count,
            "duplicate_ratio": duplicate_ratio,
            "message_history_size": len(self.message_history),
            "time_since_last_moment": time.time() - self.last_moment_time,
            "baseline_frozen": self._is_baseline_frozen(),
            "sensitivity": self.sensitivity,
            "hype_threshold": self.hype_threshold,
        }

    def reset(self):
        """Reset detector for new stream"""
        self.chat_ewma_mean = 0.5
        self.chat_ewma_var = 0.1
        self.chat_prev_velocity = 0.0
        self.chat_message_count = 0
        self.chat_last_bucket_time = time.time()

        self.audio_ewma_mean = 0.1
        self.audio_ewma_var = 0.02
        self.audio_prev_peak = 0.0

        self.message_history.clear()
        self.active_moment_time = 0.0

        self.last_moment_time = 0.0
        self.start_time = time.time()  # Reset cold-start timer

        logger.info("Moment detector reset (Approach 2: Adaptive Z-Score)")


_detector: Optional[MomentDetector] = None


def get_detector() -> MomentDetector:
    """Get or create the global moment detector"""
    global _detector
    if _detector is None:
        _detector = MomentDetector(window_size=2.0, sensitivity=0.7)
        logger.info("Moment detector initialized (sensitivity=0.7)")
    return _detector
