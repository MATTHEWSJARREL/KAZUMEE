# Agent Clip Routing Fix: Autonomous Detection → Real OBS Capture

## Issue Summary

When autonomous detection fired (chat → detector → moment), clips showed "Test Stream" placeholder instead of real OBS footage. Two bugs:

1. **Async/Await Bug**: `clip_generator_service.py:98` called `get_replay_buffer_status()` without awaiting it
   - Threw exception → fell back to test video
   - Logged: `RuntimeWarning: coroutine 'OBSAdapter.get_replay_buffer_status' was never awaited`

2. **Architecture Bug**: Backend was trying to generate clips locally, but real clips come from the agent
   - Backend has no OBS (it's a server)
   - Real clip path: moment → send_clip_command_to_agent → agent captures OBS → uploads
   - Wrong path: moment → backend generates from test video

---

## The Fix

### 1. **Correct Routing in clip_generator_service.py** (lines 42-67)

**Before (BROKEN):**
```python
def on_moment_detected(self, moment: DetectedMoment):
    # Always tries to generate clip from OBS (which fails)
    self._create_clip_record(moment)  # → get_replay_buffer_status() not awaited → exception → test video
```

**After (FIXED):**
```python
def on_moment_detected(self, moment: DetectedMoment):
    # NEW: Check if agent is online
    from backend.api.routes.agent import connected_agents
    
    if moment.streamer_id in connected_agents:
        # Agent is connected: it will capture real OBS
        # Don't generate clip here — agent handles it
        logger.info(f"Agent connected — agent will capture real OBS buffer")
        return  # ✅ Exit, let agent do the work
    
    # No agent: use test video (demo/testing mode only)
    self._create_clip_record(moment)  # Falls back to test_stream.mp4
```

**Why:** When an agent is connected for the streamer, `send_clip_command_to_agent()` (already fired in moment_detection.py) tells the agent to capture the real OBS replay buffer and upload it. The backend should NOT interfere — it should only generate test clips for testing when NO agent is connected.

### 2. **Fix Async/Await Bug** (lines 95-103)

**Before:**
```python
replay_path = self.obs_adapter.get_replay_buffer_status()  # ❌ Not awaited
if replay_path and os.path.exists(replay_path):
    video_source = replay_path
```

**After:**
```python
# Backend fallback (test video mode) doesn't access OBS
# Real clips come from agent via send_clip_command_to_agent
logger.debug(f"Backend clip generator (test video mode): not accessing OBS")
```

**Why:** Since this is sync context (callback), we can't await async calls. But we don't NEED to — backend should only use test video for demo. Real clips come from the agent.

### 3. **Ensure Agent Callback Registered First** (main.py, lines 597-618)

**Before:**
```python
# Clip generator wired first (might run before agent callback)
detector.on_moment_detected(clip_generator.on_moment_detected)
# Agent callback registered later (lazy, on first API call)
```

**After:**
```python
# Register agent callback FIRST at startup
from backend.api.routes.moment_detection import _register_agent_callback
_register_agent_callback()
print("[OK] Detector wired to Agent (send_clip_command_to_agent)")

# Then wire clip generator as fallback
detector.on_moment_detected(clip_generator.on_moment_detected)
print("[OK] Clip Generator (fallback for demo/test)")
```

**Why:** Ensures when moment fires, agent callback sends clip command BEFORE clip generator runs. Agent gets priority.

---

## Data Flow: Before vs After

### Before (BROKEN)
```
Moment detected
    ↓
clip_generator.on_moment_detected()
    ├→ get_replay_buffer_status() [not awaited]
    ├→ exception
    ├→ falls back to test_stream.mp4
    └→ backend generates clip from test video  ❌ WRONG (shows "Test Stream")

send_clip_command_to_agent() never fires OR fires too late
```

### After (FIXED)
```
Moment detected
    ↓
on_moment_detected_send_clip_command() [agent callback]
    └→ send_clip_command_to_agent(streamer_id)
       └→ agent receives clip command → captures real OBS → uploads  ✅ REAL CLIP

Then (if agent not connected):
clip_generator.on_moment_detected() [fallback]
    ├→ check: agent connected?
    ├→ YES: exit (agent will handle it)
    ├→ NO: use test video (demo only)  ✅ TEST CLIP FOR DEMO
```

---

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| **backend/core/clip_generator_service.py** | 42-67 | Check if agent connected; if YES, defer to agent |
| **backend/core/clip_generator_service.py** | 95-119 | Remove async/await bug, clarify test video is fallback only |
| **backend/main.py** | 597-618 | Register agent callback first, then clip generator as fallback |

---

## Expected Logs: Moment Detection with Agent Connected

```
[CHAT→DETECTOR] Streamer 7: fed 30 messages
[MOMENT→AGENT] 🎬 MOMENT FIRED for streamer 7 | Score: 87/100
[MOMENT→AGENT] send_clip_command_to_agent() registry id=0x12345678
[CLIP COMMAND] ✅ Sent clip command to streamer 7
  ← Agent receives this and captures OBS replay buffer
[CLIP GENERATOR] Moment fired for streamer 7
[CLIP GENERATOR] Agent connected for streamer 7 — agent will capture real OBS buffer
  ← Backend defers; doesn't create test clip
```

**Result:** Dashboard shows real clip from agent's OBS buffer ✅

---

## Expected Logs: Moment Detection WITHOUT Agent (Demo/Testing)

```
[CHAT→DETECTOR] Streamer 99: fed 30 messages
[MOMENT→AGENT] 🎬 MOMENT FIRED for streamer 99 | Score: 75/100
[CLIP COMMAND] ❌ No agent connected for streamer 99
  ← send_clip_command_to_agent returns False; agent offline
[CLIP GENERATOR] Moment fired for streamer 99
[CLIP GENERATOR] Agent NOT connected for streamer 99 — using test video (demo mode)
[CLIP GENERATOR] TEST MODE: Using demo video: backend/data/test_videos/test_stream.mp4
[CLIP GENERATOR] Test clip created (no agent connected)
```

**Result:** Dashboard shows test clip (demo only) ✅

---

## Testing

### Test 1: Moment with Connected Agent
```bash
# Prerequisites:
# 1. Agent running and connected (tray icon green)
# 2. OBS with replay buffer enabled and running

# Trigger:
python scripts/test_chat_to_detector.py

# Expected in logs:
[CLIP COMMAND] ✅ Sent clip command to streamer X
[CLIP GENERATOR] Agent connected ... will capture real OBS buffer
[CLIP NOW] Clip saved to: /uploads/agent_clip_xxx.mp4

# Expected in dashboard:
Clip shows real OBS footage (not "Test Stream")
```

### Test 2: Moment WITHOUT Agent (Demo Mode)
```bash
# Prerequisites:
# 1. No agent running
# 2. Test video exists: backend/data/test_videos/test_stream.mp4

# Trigger:
python scripts/test_chat_to_detector.py

# Expected in logs:
[CLIP COMMAND] ❌ No agent connected for streamer X
[CLIP GENERATOR] TEST MODE: Using demo video
[CLIP GENERATOR] Test clip created (no agent connected)

# Expected in dashboard:
Clip shows "Test Stream" placeholder (demo only — no agent)
```

---

## Architecture Summary

**Three Paths for Clip Creation:**

1. **Dashboard Button (Manual)** → `/api/moments/capture` → `send_clip_command_to_agent()` → Agent captures
2. **Autonomous Detection (Chat)** → `poll_chat_events()` → detector → `on_moment_detected_send_clip_command()` → `send_clip_command_to_agent()` → Agent captures
3. **Demo/Testing (No Agent)** → clip_generator fallback → test_stream.mp4 (backend generates)

**When Agent Connected:** Paths 1 & 2 send command to agent, agent captures real OBS, agent uploads clip. Backend stores in DB.

**When Agent Offline:** Path 3 creates test clip from demo video. Used for testing autonomous detection without a real streamer.

---

## Rollout Checklist

- ✅ Fixed async/await bug (no more coroutine warnings)
- ✅ Fixed routing (agent gets priority, backend is fallback)
- ✅ Ensured agent callback registered at startup
- ✅ Clarified in logs when test video is used (demo mode only)
- ✅ No changes to agent code (hotkey still works)
- ✅ No changes to dashboard (just shows correct clips now)

---

## Next Steps (Still TODO)

1. Deploy backend with these fixes
2. Run test with agent connected → verify real OBS clip appears
3. Run test without agent → verify test video clip appears (demo)
4. Monitor logs for "[CLIP COMMAND] ✅ Sent clip command" on autonomous moments
