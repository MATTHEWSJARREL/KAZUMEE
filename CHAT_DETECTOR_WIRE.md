# Chat → Detector Wire: Implementation Summary

## Overview
Connected YouTube/Twitch chat ingestion to the moment detector via a background poller task. Chat messages stored in `stream_events` table now feed the detector in real-time for autonomous clip generation.

---

## Files Changed

### 1. `backend/core/ingestion.py`
**Added:**
- `import logging` + logger setup
- `CHAT_POLLER_INTERVAL = 2` (poll every 2 seconds)
- `_chat_poller_last_id: dict[int, int]` (in-memory tracking of last-processed ID per streamer)
- **NEW FUNCTION:** `poll_chat_events(stop_event: asyncio.Event)`
  - Polls `stream_events` table for rows where `event_type='chat_message'`
  - Groups by `streamer_id` to handle multi-streamer scenarios
  - Tracks last-processed ID per streamer to avoid double-processing
  - Calls `detector.add_chat_message(streamer_id, source=platform, message)`
  - Logs progress: `[CHAT→DETECTOR] Streamer X: fed N messages`
  - Runs every 2 seconds in background loop
  - **No database migration needed** (uses in-memory tracking)

**Why this approach:**
- Simple: no schema changes or migrations
- Per-streamer tracking: handles multi-tenant correctly
- Survives single-worker deployment (in-memory OK because workers=1)
- 2s interval balances latency vs CPU (detector debounce is 30s anyway)

---

### 2. `backend/main.py`
**Changes:**

Line 66:
```python
# Before:
from backend.core.ingestion import ingestion_loop

# After:
from backend.core.ingestion import ingestion_loop, poll_chat_events
```

Line 595:
```python
# Before:
app.state.ingestion_task = asyncio.create_task(ingestion_loop(stop_event))

# After:
app.state.ingestion_task = asyncio.create_task(ingestion_loop(stop_event))
app.state.chat_poller_task = asyncio.create_task(poll_chat_events(stop_event))
```

Line 707 (shutdown cleanup):
```python
# Added:
if hasattr(app.state, "chat_poller_task"):
    try:
        await app.state.chat_poller_task
    except Exception:
        pass
```

**Why:**
- Starts chat poller alongside ingestion loop
- Ensures graceful shutdown of poller task
- Same process = same registry (agent WS, detector, poller all see same instances)

---

### 3. `backend/api/routes/moment_detection.py`
**Changes in `on_moment_detected_send_clip_command()`:**

Before:
```python
logger.info(f"[MOMENT→AGENT] Moment detected for streamer {streamer_id} | "
           f"Score: {moment.combined_score}/100 | Connected agents: {all_connected}")
```

After:
```python
logger.info(f"[MOMENT→AGENT] 🎬 MOMENT FIRED for streamer {streamer_id} | "
           f"Score: {moment.combined_score}/100 | Context: {moment.context} | Connected agents: {all_connected}")
```

**Why:**
- Clearer distinction in logs when moments fire
- Includes context to identify real chat vs test
- Emoji helps grep for production moments

---

## Data Flow

```
YouTube/Twitch API
       ↓
ingestion_loop() → poll_youtube_once()
       ↓
stream_events table [chat_message rows]
  (id, streamer_id, platform="youtube", event_type="chat_message", message)
       ↓
poll_chat_events() [NEW - runs every 2s]
  - Queries stream_events WHERE event_type='chat_message' ORDER BY id ASC
  - Filters to new rows (id > last_processed_id per streamer)
  - Calls detector.add_chat_message(streamer_id, platform, message)
  - Logs: [CHAT→DETECTOR] Streamer X: fed N messages
       ↓
MomentDetector
  - Updates EWMA baselines with chat velocity
  - Triggers _check_moment_triggered() on each message
  - When moment score > threshold: fires DetectedMoment callback
       ↓
on_moment_detected_send_clip_command() [existing callback]
  - Logs: [MOMENT→AGENT] 🎬 MOMENT FIRED ...
  - Calls send_clip_command_to_agent(streamer_id)
       ↓
Agent WebSocket → OBS Replay Buffer Saved → Clip Uploaded
```

---

## Key Design Decisions

### 1. **In-Memory Tracking (No Migration)**
- `_chat_poller_last_id: dict[int, int]` tracks per-streamer progress
- Survives process restart because:
  - On startup, `last_id` defaults to 0
  - Poller scans from stream_events again
  - Existing messages are re-fed but deduplicated (same event_id = no duplicate insertion)
- **No DB migration required**

### 2. **Single Registry (workers=1)**
- Poller runs in main process
- Detector is singleton (get_detector())
- Agent registry is module-level in agent.py
- All three see same instances → moment fires → agent gets clip command

### 3. **2-Second Poll Interval**
- Detector's debounce_interval is 30 seconds
- Chat velocity window is 2 seconds
- 2s poller matches detector's window size
- Latency: chat appears in DB → poller picks it up in ≤2s → detector evaluates

### 4. **Per-Streamer Grouping**
- Handles multi-tenant correctly
- Each streamer's chat spike is independent
- Detector is global but moment detection is per-streamer (streamer_id in DetectedMoment)

---

## Testing

### Quick Verification
```bash
python scripts/verify_chat_poller.py
```
Checks:
- ✅ Imports work
- ✅ StreamEvent model exists
- ✅ Detector initialized
- ✅ main.py wiring is correct

### End-to-End Test
```bash
# Terminal 1: Start backend
cd backend && python -m uvicorn main:app --reload --log-level debug

# Terminal 2: Run test
python scripts/test_chat_to_detector.py
```

What the test does:
1. Gets/creates a test streamer
2. Inserts 30 hype chat messages into stream_events
3. Waits 3s for poller to pick them up (max 2s per poll + 1s buffer)
4. Watches for detector to fire moment
5. Checks if a clip was created
6. Logs success or failure with guidance

Expected output:
```
======================================================================
TEST: Stream Events → Chat Poller → Detector → Clip
======================================================================

[Step 1] Setup test streamer
✅ Using existing test streamer: id=7, username=test_chat_to_detector

[Step 2] Simulate chat spike
🔵 Inserting 30 chat messages for streamer 7...
✅ Inserted 30 messages into stream_events

[Step 3] Wait for detector to fire and clip to be created
⏳ Waiting 3s for chat poller to process messages...
📊 Baseline clips for streamer 7: 5
⏱️  Waiting... (1s/20s)
✅ NEW CLIP CREATED! Total clips: 6
   Clip: id=42, title=EPIC MOMENT, status=pending
   Created: 2026-08-25 12:34:56.789, requested_by: auto_detection

======================================================================
✅ SUCCESS: End-to-end flow works!
   Chat → StreamEvents → ChatPoller → Detector → Clip ✓
======================================================================
```

Backend logs should show:
```
[CHAT→DETECTOR] Streamer 7: fed 30 messages
[MOMENT→AGENT] 🎬 MOMENT FIRED for streamer 7 | Score: 87/100 | Context: Chat spike (30 msgs) + moderate audio
[MOMENT→AGENT] ✅ Clip command sent to streamer 7
[CLIP NOW] Clip saved to: /clips/auto_clip_xxx.mp4
```

---

## Logging Prefixes

### Chat Poller
- `[CHAT→DETECTOR]` — poller feeding messages to detector
- `[CHAT→DETECTOR] Streamer X: fed N messages` — log per-streamer progress every poll
- `[CHAT→DETECTOR] Poller error: ...` — errors in poller task

### Moment Detector
- `[MOMENT→AGENT]` — moment detected and clip command sent
- `[MOMENT→AGENT] 🎬 MOMENT FIRED for streamer X` — moment fires
- `[MOMENT→AGENT] ✅ Clip command sent to streamer X` — clip command delivered
- `[MOMENT→AGENT] ❌ Agent offline for streamer X` — agent not connected

### Clip Ingestion
- `[CLIP NOW]` — clip captured (existing, no change)

---

## What's NOT Done (Still TODO)

1. **YouTube OAuth UI** — Streamers need frontend to authorize YouTube
   - Backend supports it (PlatformConnection model)
   - No UI in /settings yet
   - Workaround: manually insert PlatformConnection rows

2. **Twitch EventSub Webhook** — Twitch ingestion uses polling fallback
   - Backend has auto_subscribe_twitch() but needs webhook endpoint
   - Chat still flows via polling for now

3. **Mobile Dashboard** — Dashboard needs mobile responsiveness (auth page is done)

---

## Troubleshooting

### Poller not running?
- Check logs for `[CHAT→DETECTOR]` — should appear every 2s
- If missing: check if backend started correctly (lifespan event)
- Verify: `app.state.chat_poller_task` is created

### Detector not firing?
- Poller feeding messages? Check `[CHAT→DETECTOR]` logs
- Detector in cold-start? First 60s uses conservative threshold
- Debounce active? Moments are debounced 30s apart
- Try: Insert 50+ messages rapidly, ensure audio peak > 0.3

### Clip not created?
- Agent connected? Check `[CLIP COMMAND]` and `[AGENT REGISTRY]` logs
- OBS running? Replay buffer must be enabled
- File saved? Check `/clips` directory or S3 bucket

---

## Performance Notes

- Poller queries all stream_events every 2s (simple but could be optimized with `created_at > last_check_time`)
- No index needed yet (table should be small for MVP)
- Detector EWMA updates happen on every message (expected)
- Single-worker deployment ensures no registry split

---

## Migration Path (Future)

If we want to scale beyond single worker:
1. Add `processed: BOOLEAN DEFAULT FALSE` column to stream_events (DB migration)
2. Poller marks processed=true after feeding to detector
3. Multiple workers can safely poll without double-processing

For now: in-memory tracking + workers=1 is simplest.
