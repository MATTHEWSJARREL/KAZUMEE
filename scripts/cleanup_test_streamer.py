#!/usr/bin/env python3
"""
Cleanup Script: Delete test streamer 8 and all associated data.

Usage:
  python scripts/cleanup_test_streamer.py         # Delete test_chat_to_detector streamer
  python scripts/cleanup_test_streamer.py --id 8  # Delete streamer with id=8
"""

import sys
import logging

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


def cleanup_streamer(db, streamer_id: int = None, username: str = None):
	"""Delete streamer and all associated data (stream_events, clips)."""

	if not streamer_id and not username:
		logger.error("❌ Must provide either streamer_id or username")
		return False

	# Find streamer
	if streamer_id:
		streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
	else:
		streamer = db.query(Streamer).filter(Streamer.username == username).first()

	if not streamer:
		logger.error(f"❌ Streamer not found (id={streamer_id}, username={username})")
		return False

	logger.info(f"🗑️  Deleting streamer: id={streamer.id}, username={streamer.username}")

	try:
		# Delete all stream_events for this streamer
		deleted_events = db.query(StreamEvent).filter(
			StreamEvent.streamer_id == streamer.id
		).delete()
		logger.info(f"   ✅ Deleted {deleted_events} stream_events")

		# Delete all clips for this streamer
		deleted_clips = db.query(Clip).filter(
			Clip.streamer_id == streamer.id
		).delete()
		logger.info(f"   ✅ Deleted {deleted_clips} clips")

		# Delete the streamer
		db.delete(streamer)
		logger.info(f"   ✅ Deleted streamer {streamer.username}")

		db.commit()
		logger.info(f"\n✅ Cleanup complete! Deleted all data for streamer {streamer.username}")
		return True

	except Exception as e:
		logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
		db.rollback()
		return False


def main():
	"""Parse args and run cleanup."""
	db = SessionLocal()
	try:
		logger.info("=" * 70)
		logger.info("CLEANUP: Delete test streamer and all associated data")
		logger.info("=" * 70 + "\n")

		# Parse arguments
		streamer_id = None
		username = "test_chat_to_detector"  # Default test streamer

		if len(sys.argv) > 1:
			if sys.argv[1] == "--id":
				if len(sys.argv) > 2:
					try:
						streamer_id = int(sys.argv[2])
						username = None  # Use ID instead
					except ValueError:
						logger.error(f"❌ Invalid streamer_id: {sys.argv[2]}")
						return 1
			else:
				username = sys.argv[1]

		# Run cleanup
		success = cleanup_streamer(db, streamer_id=streamer_id, username=username)
		logger.info("=" * 70)

		return 0 if success else 1

	except Exception as e:
		logger.error(f"❌ Error: {e}", exc_info=True)
		return 1
	finally:
		db.close()


if __name__ == "__main__":
	exit(main())
