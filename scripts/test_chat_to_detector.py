#!/usr/bin/env python3
"""
Test Script: Stream Events → Chat Poller → Detector → Clip Capture
Inserts fake chat_message rows into stream_events and verifies end-to-end flow.

Usage:
  python scripts/test_chat_to_detector.py           # Use throwaway test streamer
  python scripts/test_chat_to_detector.py 7         # Test against streamer 7 (real connected agent)
  python scripts/test_chat_to_detector.py 99        # Test against any streamer_id
"""

import sys
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Must run from project root
sys.path.insert(0, '/c/Users/ADMIN/Desktop/kazumi\\ 1')

from backend.database.session import SessionLocal
from backend.database.models.stream_event import StreamEvent
from backend.database.models.streamer import Streamer
from backend.database.models.clip import Clip


def get_or_create_test_streamer(db, streamer_username="test_chat_to_detector") -> int:
    """Get or create a test streamer."""
    streamer = db.query(Streamer).filter(Streamer.username == streamer_username).first()
    if streamer:
        logger.info(f"✅ Using existing test streamer: id={streamer.id}, username={streamer_username}")
        return streamer.id

    # Create new test streamer
    streamer = Streamer(
        username=streamer_username,
        display_name="Test Chat-to-Detector Streamer",
        platform="test"
    )
    db.add(streamer)
    db.commit()
    db.refresh(streamer)
    logger.info(f"✅ Created test streamer: id={streamer.id}, username={streamer_username}")
    return streamer.id


def insert_chat_spike(db, streamer_id: int, num_messages: int = 30, spike_name: str = "test_spike"):
    """Insert a burst of chat_message rows into stream_events."""
    logger.info(f"\n🔵 Inserting {num_messages} chat messages for streamer {streamer_id}...")

    hype_messages = [
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

    for i in range(num_messages):
        message = hype_messages[i % len(hype_messages)]
        event = StreamEvent(
            streamer_id=streamer_id,
            platform="youtube",
            event_type="chat_message",
            event_id=f"test_{spike_name}_{i}_{int(time.time())}",
            user_id=f"test_user_{i}",
            username=f"viewer_{i}",
            message=message,
            payload={"test": True, "spike": spike_name}
        )
        db.add(event)

    db.commit()
    logger.info(f"✅ Inserted {num_messages} messages into stream_events")
    return num_messages


def wait_for_detector_and_clips(db, streamer_id: int, timeout: int = 20, initial_delay: int = 3):
    """
    Wait for:
    1. Chat poller to pick up messages (takes up to 2s per poll)
    2. Detector to fire (happens when message is added)
    3. Clip to be created (should be fast if agent is connected)
    """
    logger.info(f"\n⏳ Waiting {initial_delay}s for chat poller to process messages...")
    time.sleep(initial_delay)

    start_time = time.time()
    last_clip_count = db.query(Clip).filter(Clip.streamer_id == streamer_id).count()

    logger.info(f"📊 Baseline clips for streamer {streamer_id}: {last_clip_count}")

    while time.time() - start_time < timeout:
        current_clip_count = db.query(Clip).filter(Clip.streamer_id == streamer_id).count()

        if current_clip_count > last_clip_count:
            logger.info(f"✅ NEW CLIP CREATED! Total clips: {current_clip_count}")

            # Show the new clip
            new_clip = db.query(Clip).filter(
                Clip.streamer_id == streamer_id
            ).order_by(Clip.created_at.desc()).first()

            if new_clip:
                logger.info(f"   Clip: id={new_clip.id}, title={new_clip.title}, status={new_clip.status}")
                logger.info(f"   Created: {new_clip.created_at}, requested_by: {new_clip.requested_by_type}")

            return True

        logger.debug(f"⏱️  Waiting... ({int(time.time() - start_time)}s/{timeout}s)")
        time.sleep(1)

    logger.warning(f"⏰ Timeout: No new clip created in {timeout}s")
    logger.warning(f"   Check backend logs for [CHAT→DETECTOR] and [MOMENT→AGENT]")
    return False


def main(streamer_id: int = None):
    """
    Run the end-to-end test.

    Args:
        streamer_id: If provided, test against this streamer (use real agent).
                     If None, create/use a throwaway test streamer.
    """
    db = SessionLocal()
    try:
        logger.info("=" * 70)
        logger.info("TEST: Stream Events → Chat Poller → Detector → Clip")
        logger.info("=" * 70)

        # Step 1: Get streamer (use provided or create test)
        logger.info("\n[Step 1] Setup streamer")
        if streamer_id is not None:
            # Use provided streamer_id (should have connected agent)
            streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
            if not streamer:
                logger.error(f"❌ Streamer {streamer_id} not found in database")
                return 1
            logger.info(f"✅ Using streamer: id={streamer.id}, username={streamer.username}")
        else:
            # Create/use throwaway test streamer
            logger.info("Using throwaway test streamer (no real agent expected)")
            streamer_id = get_or_create_test_streamer(db)

        # Step 2: Insert chat spike
        logger.info("\n[Step 2] Simulate chat spike")
        spike_name = f"test_run_{int(time.time())}"
        num_messages = insert_chat_spike(db, streamer_id, num_messages=30, spike_name=spike_name)

        # Step 3: Wait for detector to fire and clip to be created
        logger.info("\n[Step 3] Wait for detector to fire and clip to be created")
        clip_created = wait_for_detector_and_clips(db, streamer_id, timeout=20, initial_delay=3)

        # Step 4: Report results
        logger.info("\n" + "=" * 70)
        if clip_created:
            logger.info("✅ SUCCESS: End-to-end flow works!")
            logger.info("   Chat → StreamEvents → ChatPoller → Detector → Clip ✓")
            if streamer_id:
                logger.info(f"   Real OBS clip captured by agent for streamer {streamer_id}")
        else:
            logger.warning("⚠️  No clip created. Possible issues:")
            logger.warning("   1. Chat poller not running (check backend logs for [CHAT→DETECTOR])")
            logger.warning("   2. Detector not triggering (might be cold-start or debounce)")
            logger.warning("   3. Agent not connected (check [MOMENT→AGENT] logs)")
            logger.warning("   4. Clip creation failed (check backend for errors)")
        logger.info("=" * 70)

        return 0 if clip_created else 1

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    # Parse CLI arguments
    streamer_id = None
    if len(sys.argv) > 1:
        try:
            streamer_id = int(sys.argv[1])
            print(f"\n🎯 Testing against streamer {streamer_id}\n")
        except ValueError:
            print(f"❌ Invalid streamer_id: {sys.argv[1]} (must be integer)")
            print(f"\nUsage: python scripts/test_chat_to_detector.py [streamer_id]")
            print(f"Examples:")
            print(f"  python scripts/test_chat_to_detector.py       # Use test streamer")
            print(f"  python scripts/test_chat_to_detector.py 7     # Test streamer 7\n")
            sys.exit(1)

    exit(main(streamer_id=streamer_id))
