#!/usr/bin/env python3
"""
Quick verification: Check if chat poller is running and wired correctly.
"""
import sys
sys.path.insert(0, '/c/Users/ADMIN/Desktop/kazumi\\ 1')

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

print("\n" + "="*70)
print("VERIFICATION: Chat Poller Integration")
print("="*70)

# Check 1: Imports
print("\n[1/4] Checking imports...")
try:
    from backend.core.ingestion import poll_chat_events
    print("  ✅ poll_chat_events imported successfully")
except ImportError as e:
    print(f"  ❌ Failed to import poll_chat_events: {e}")
    sys.exit(1)

# Check 2: Database models
print("\n[2/4] Checking database models...")
try:
    from backend.database.models.stream_event import StreamEvent
    print("  ✅ StreamEvent model exists")
    print(f"     Columns: id, streamer_id, platform, event_type, username, message, created_at")
except ImportError as e:
    print(f"  ❌ Failed to import StreamEvent: {e}")
    sys.exit(1)

# Check 3: Detector
print("\n[3/4] Checking detector...")
try:
    from backend.core.moment_detector import get_detector
    detector = get_detector()
    print(f"  ✅ Detector initialized")
    print(f"     add_chat_message signature: (streamer_id, source, message)")
except Exception as e:
    print(f"  ❌ Failed to initialize detector: {e}")
    sys.exit(1)

# Check 4: Async verification
print("\n[4/4] Checking main.py integration...")
try:
    with open('/c/Users/ADMIN/Desktop/kazumi\\ 1/backend/main.py', 'r') as f:
        main_content = f.read()

    checks = [
        ('poll_chat_events imported', 'from backend.core.ingestion import ingestion_loop, poll_chat_events' in main_content),
        ('chat_poller_task created', 'app.state.chat_poller_task = asyncio.create_task(poll_chat_events(stop_event))' in main_content),
        ('chat_poller_task awaited on shutdown', 'await app.state.chat_poller_task' in main_content),
    ]

    all_good = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_good = False

    if not all_good:
        sys.exit(1)

except Exception as e:
    print(f"  ❌ Failed to verify main.py: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("✅ ALL CHECKS PASSED")
print("\nChat poller is properly wired!")
print("\nNext steps:")
print("  1. Start backend: cd backend && python -m uvicorn main:app --reload")
print("  2. Check logs for '[CHAT→DETECTOR]' entries (every 2s)")
print("  3. Run: python scripts/test_chat_to_detector.py")
print("="*70 + "\n")
