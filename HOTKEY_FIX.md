# Hotkey Crash Fix: Ctrl+Shift+C

## Issue
Agent crashed on startup with:
```
AttributeError: c
  File "enum.py", line ...
```

**Root cause:** Line 597 in `kazumee-agent.py` used `Key.c` which doesn't exist. The `Key` enum only contains special keys (ctrl, shift, alt, etc.), not regular character keys like 'c'.

---

## Solution Applied

### 1. Use GlobalHotKeys String API (Line 577-606)

**Before (BROKEN):**
```python
hotkey_combo = {Key.ctrl_l, Key.shift_l, Key.c}  # ❌ Key.c doesn't exist!
current_keys = set()
def on_press(key):
    try:
        current_keys.add(key)
        if hotkey_combo.issubset(current_keys):
            on_hotkey_press()
    except AttributeError:
        pass
```

**After (FIXED):**
```python
from pynput.keyboard import GlobalHotKeys

hotkeys = GlobalHotKeys({'<ctrl>+<shift>+c': on_hotkey_press})
hotkeys.start()
```

**Why:** 
- String-based hotkey definition is simpler and less error-prone
- pynput's `GlobalHotKeys` class handles the parsing correctly
- No need to manually track key state or reference `Key` enum

### 2. Wrap Entire Setup in Try/Except (Line 587-606)

**Any failure** (OS refusal, pynput missing, bad combo) now:
- ✅ Logs a warning (agent continues running)
- ✅ Falls back to "Clip Now" button only
- ❌ Does NOT crash the agent

```python
try:
    hotkeys = GlobalHotKeys({'<ctrl>+<shift>+c': on_hotkey_press})
    hotkeys.start()
    status("ok", "Global hotkey enabled: Ctrl+Shift+C to clip...")
    return hotkeys
except Exception as e:
    status("warn", f"Hotkey setup failed (agent will still work): {e}")
    status("info", "  Use 'Clip Now' button in dashboard instead")
    return None
```

### 3. Clean Up on Shutdown (Line 673-679)

**Added hotkey cleanup:**
```python
if hotkey_listener:
    try:
        hotkey_listener.stop()
    except Exception:
        pass
```

---

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `kazumee-agent.py` | 577-606 | Rewrite `setup_hotkey_listener()` with GlobalHotKeys |
| `kazumee-agent.py` | 673-679 | Add hotkey cleanup on shutdown |

---

## Testing

### 1. **Launch Agent** (should NOT crash)
```bash
cd dist/KazumeeAgent
.\KazumeeAgent.exe
```

Expected:
```
Global hotkey enabled: Ctrl+Shift+C to clip (no alt-tab needed)
Tray icon appears → green dot
Agent is running ✅
```

### 2. **Press Hotkey** (should capture clip)
```
1. Launch OBS with replay buffer enabled
2. Start streaming (or any content)
3. Press Ctrl+Shift+C
```

Expected in agent logs:
```
🎬 HOTKEY: Ctrl+Shift+C pressed - triggering clip...
[CLIP NOW] Clip saved to: ...
```

### 3. **Dashboard "Clip Now"** (should always work)
```
1. Open dashboard at https://kazumee.vercel.app
2. Click "🎬 Clip Now" button
```

Expected:
```
✅ Clip command sent! Your agent is capturing...
OR
❌ Agent offline (if not running)
```

**Works regardless of hotkey status** ✅

### 4. **Hotkey Graceful Failure** (test recovery)
```
1. Rename pynput package temporarily (simulate missing import)
2. Launch agent
```

Expected:
```
⚠️  Hotkey setup failed (agent will still work): ...
📝 Use 'Clip Now' button in dashboard instead
[Agent continues running]
✅ Dashboard works fine
```

---

## Build Info

**New Build:**
- Timestamp: 2026-08-25 13:42:18
- Size: 34.1 MB (zipped)
- File: `KazumeeAgent.zip`
- Status: ✅ Ready to distribute

**What's Bundled:**
- ✅ pynput 1.8.2 (global hotkey support)
- ✅ Fixed hotkey initialization
- ✅ Graceful fallback to dashboard-only mode
- ✅ System tray support
- ✅ Replay buffer capture
- ✅ Cloud WebSocket connection

---

## Key Improvements

| Before | After |
|--------|-------|
| ❌ Crashes on `Key.c` reference | ✅ Uses correct `GlobalHotKeys` API |
| ❌ No error protection | ✅ Try/except guards entire setup |
| ❌ Unclear failure mode | ✅ Logs warning, suggests workaround |
| ❌ Hotkey failure = app crash | ✅ Hotkey failure = dashboard fallback works |

---

## Backward Compatibility

- ✅ Hotkey still works the same way (Ctrl+Shift+C)
- ✅ Dashboard "Clip Now" unchanged
- ✅ Agent token system unchanged
- ✅ OBS connection unchanged
- ✅ No config file changes needed

---

## Rollout

**Distribution:**
- Download: `KazumeeAgent.zip`
- Extract anywhere
- Run `KazumeeAgent.exe`
- First run: enter token + OBS password
- Hotkey enabled automatically (if pynput works)
- If hotkey fails: use dashboard button

**No streamer action needed.** Drop-in replacement for any previous version.
