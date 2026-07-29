"""
YouTube Chat Simulator for Testing

Simulates realistic chat patterns to test moment detection
without needing a real YouTube stream.
"""

import asyncio
import random
import logging
import time
from typing import List, Dict

logger = logging.getLogger(__name__)


class ChatPattern:
    """Defines a chat behavior pattern"""

    def __init__(self, name: str, message_count: int, duration_seconds: float = 2.0):
        self.name = name
        self.message_count = message_count
        self.duration = duration_seconds

    def __repr__(self):
        return f"{self.name} ({self.message_count} msgs in {self.duration}s)"


# Pre-defined patterns
PATTERNS = {
    "normal": ChatPattern("Normal Chat", 2, 2.0),
    "active": ChatPattern("Active Chat", 5, 2.0),
    "spike": ChatPattern("Chat Spike", 15, 2.0),
    "burst": ChatPattern("Chat Burst", 30, 2.0),
    "epic": ChatPattern("EPIC Moment", 50, 1.5),
}

SAMPLE_MESSAGES = [
    "OMEGALUL",
    "What??",
    "CLIP IT",
    "NO WAY",
    "INSANE",
    "GG",
    "HOW?",
    "THAT WAS SICK",
    "WHAT DID I JUST WATCH",
    "POGGERS",
    "wtf",
    "amazing",
    "best stream ever",
    "lmao",
    "that was crazy",
    "YOOOO",
    "LETS GOOO",
    "IMPOSSIBLE",
    "CLUTCH",
    "LEGEND",
]

SAMPLE_USERS = [
    f"viewer_{i}" for i in range(1, 101)
]


async def send_chat_event(message: str, username: str = None):
    """Send a chat event to the moment detector"""
    if not username:
        username = random.choice(SAMPLE_USERS)

    try:
        import requests

        response = requests.post(
            "http://localhost:8000/api/moments/chat-event",
            json={
                "source": "simulated",
                "username": username,
                "message": message
            },
            timeout=5
        )

        if response.status_code == 200:
            logger.debug(f"Chat sent: {username}: {message}")
            return True
        else:
            logger.warning(f"Chat send failed: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Failed to send chat event: {e}")
        return False


async def simulate_pattern(pattern: ChatPattern, audio_peak: float = None):
    """
    Simulate a chat pattern.

    Args:
        pattern: ChatPattern to simulate
        audio_peak: Optional audio peak to send simultaneously (0.0-1.0)
    """
    logger.info(f"Simulating: {pattern}")

    interval = pattern.duration / pattern.message_count

    # Send chat events
    for i in range(pattern.message_count):
        message = random.choice(SAMPLE_MESSAGES)
        await send_chat_event(message)

        # Add small delay between messages
        if i < pattern.message_count - 1:
            await asyncio.sleep(interval)

    # Send audio peak if specified
    if audio_peak is not None:
        logger.info(f"Adding audio peak: {audio_peak}")
        try:
            import requests
            requests.post(
                "http://localhost:8000/api/moments/audio-event",
                json={
                    "source": "simulated",
                    "peak_value": audio_peak
                },
                timeout=5
            )
        except Exception as e:
            logger.error(f"Failed to send audio peak: {e}")

    logger.info(f"Pattern complete: {pattern.name}")


async def simulate_moment(
    chat_intensity: str = "spike",
    audio_peak: float = 0.8,
    wait_after_seconds: float = 0
):
    """
    Simulate a complete moment (chat spike + audio peak).

    This is the main function for testing moment detection.

    Args:
        chat_intensity: "normal", "active", "spike", "burst", or "epic"
        audio_peak: Audio peak value (0.0-1.0), None to skip
        wait_after_seconds: Seconds to wait after simulation
    """
    pattern = PATTERNS.get(chat_intensity, PATTERNS["spike"])
    await simulate_pattern(pattern, audio_peak)

    if wait_after_seconds > 0:
        logger.info(f"Waiting {wait_after_seconds}s...")
        await asyncio.sleep(wait_after_seconds)


async def simulate_stream_session(
    duration_minutes: int = 10,
    moments_per_minute: float = 1.0
):
    """
    Simulate a complete stream session with periodic moments.

    Args:
        duration_minutes: How long to simulate (minutes)
        moments_per_minute: How many moments per minute to generate
    """
    logger.info(f"Starting stream simulation: {duration_minutes} min, {moments_per_minute} moments/min")

    start_time = time.time()
    interval = 60 / moments_per_minute  # Seconds between moments
    last_moment_time = start_time

    while time.time() - start_time < duration_minutes * 60:
        now = time.time()

        # Trigger moment at regular intervals
        if now - last_moment_time >= interval:
            # Random intensity
            intensity = random.choice(["active", "spike", "burst"])
            audio_peak = random.uniform(0.6, 0.95)

            logger.info(f"[{int((now - start_time)/60)}m] Moment triggered")
            await simulate_moment(intensity, audio_peak)

            last_moment_time = now

        # Check for termination
        await asyncio.sleep(0.5)

    logger.info("Stream simulation complete")


# CLI entry point
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(message)s'
    )

    if len(sys.argv) > 1:
        intensity = sys.argv[1]
        asyncio.run(simulate_moment(intensity))
    else:
        # Default: single spike
        asyncio.run(simulate_moment("spike", 0.85))
