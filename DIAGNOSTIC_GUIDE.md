# 🔍 DIAGNOSTIC GUIDE - TEST EACH FEATURE

**Date:** 2026-07-14  
**What:** Systematic testing of all core features  
**Why:** Identify which features work vs need fixes

---

## ✅ FIXES APPLIED

```
1. ✅ Onboarding redirect: HomePage now checks onboarding_complete
2. ✅ Clip Now button: Added /api/clips/save-now endpoint
3. ✅ Auth flow: Fixed credentials + database session bugs
```

---

## 🧪 TESTING PROTOCOL

### **SETUP (Do Once)**
1. Stop both servers: `Ctrl+C`
2. Restart backend:
   ```bash
   cd c:/Users/ADMIN/Desktop/"kazumi 1"
   python -m uvicorn backend.main:app --reload --port 8000
   ```
3. Restart frontend (new terminal):
   ```bash
   cd c:/Users/ADMIN/Desktop/"kazumi 1"/frontend/web
   npm run dev
   ```
4. Wait 10 seconds for servers to fully start
5. Open browser to `http://localhost:5173`
6. Open DevTools: `F12` → **Console tab open the entire time**

---

## 🎯 TEST 1: ONBOARDING REDIRECT

**Clear state:**
```javascript
// In DevTools Console:
localStorage.clear()
sessionStorage.clear()
location.reload()
```

**Test:**
1. Click "Start Free" on landing page
2. Enter test email: `test@example.com`
3. Enter password: `Test1234!`
4. Select role: **Streamer**
5. Click "Create Account"

**Expected Result:**
- ✅ Should redirect to `/onboarding` (Step 1 of wizard)
- ✅ Should NOT go to dashboard
- ✅ URL bar shows `localhost:5173/onboarding`

**If It Fails:**
- [ ] Check browser console for errors
- [ ] Check backend logs for auth/me response
- [ ] Verify onboarding_complete field in response: 
  ```bash
  curl -X GET http://localhost:8000/auth/me \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json"
  ```

---

## 🎯 TEST 2: CLIP NOW BUTTON

**Setup:**
1. Complete onboarding (above test)
2. Land on dashboard
3. Make sure OBS is connected (check OBS status in top-right)
4. **IMPORTANT:** Have OBS running and streaming/recording

**Test:**
1. Click **"Clip Now"** button (top right, scissors icon)
2. Observe button state

**Expected Result:**
- ✅ Button shows "Saving..." immediately
- ✅ Toast notification appears: "Clipping..."
- ✅ After 2-3 seconds, toast changes to "Clip saved!"
- ✅ Button returns to normal
- ✅ Clip appears in OBS replay buffer

**If It Fails:**
- [ ] Check console: `Failed to save clip` error?
- [ ] Is OBS actually connected? (check OBS Connection indicator)
- [ ] Check backend logs for `save_replay_buffer` execution
- [ ] Verify backend received POST to `/api/clips/save-now`:
  ```bash
  tail -f backend.log | grep "save-now\|save_replay_buffer"
  ```

---

## 🎯 TEST 3: VOICE COMMAND - CLIP THAT

**Setup:**
1. Dashboard loaded
2. OBS connected and streaming
3. Click **"Voice"** button to start listening
4. Browser should ask for microphone permission → **Allow**

**Test - Say Clearly:**
```
"Hey Zumi, clip that"
```

**Expected Result:**
- ✅ Toast appears: "Listening..."
- ✅ After 1-2 sec: "Transcribed: clip that" (in console)
- ✅ Brain Decider recognizes: "Saving clip"
- ✅ Toast: "Clip command sent"
- ✅ Clip saved in OBS

**If It Fails:**
- [ ] Is microphone working? Test with voice recorder first
- [ ] Check console for transcription output
- [ ] Check backend logs for brain decision:
  ```bash
  # Should see: "Searching for: clip that" or "Saving clip"
  tail -f backend.log | grep "Decision"
  ```
- [ ] Manually test brain decider:
  ```bash
  python3 -c "
  from backend.brain.decider import brain_decider
  result = brain_decider.decide('clip that', ['Main', 'Facecam'])
  print(result)
  "
  ```

---

## 🎯 TEST 4: VOICE COMMAND - SEARCH

**Setup:**
1. Dashboard loaded
2. Click **"Voice"** button
3. Speak clearly

**Test - Say One of These:**
```
"Pull the TikTok of backflips over Lambos"
"Find me some epic gaming highlights"
"Search for Twitch clip moments"
"Get me that viral dance"
```

**Expected Result:**
- ✅ Toast: "Listening..."
- ✅ Console shows transcribed text
- ✅ Brain Decider recognizes: "Searching for: [query]"
- ✅ Toast: "Search completed"
- ✅ Search results appear on dashboard

**If It Fails:**
- [ ] Check console for transcription
- [ ] Check backend logs for `"search_clip"` intent
- [ ] Verify Serper API key is set:
  ```bash
  echo $SERPER_API_KEY  # Should show key, not blank
  ```
- [ ] Manually test brain decider with search phrase:
  ```bash
  python3 -c "
  from backend.brain.decider import brain_decider
  result = brain_decider.decide('pull the tiktok of backflips', ['Main'])
  print(result)
  "
  ```

---

## 🎯 TEST 5: MANUAL SEARCH (Button)

**Setup:**
1. Dashboard loaded
2. Find **"Moment Finder"** panel

**Test:**
1. Type search query: "epic gaming highlights"
2. Click **"Search"** or press Enter

**Expected Result:**
- ✅ Loading spinner appears
- ✅ After 2-3 sec: Results appear with titles/URLs
- ✅ Can click results to open links

**If It Fails:**
- [ ] Check console network tab → look for `/api/moment-finder/search` request
- [ ] Does it return 200 OK or error?
- [ ] Check Serper API response in backend logs
- [ ] Verify endpoint is registered:
  ```bash
  curl -X POST http://localhost:8000/api/moment-finder/search \
    -H "Content-Type: application/json" \
    -d '{"query": "test", "platforms": ["twitch"], "limit": 3}'
  ```

---

## 📊 RESULTS MATRIX

Create a table of what you find:

| Feature | Works? | Notes |
|---------|--------|-------|
| Onboarding redirect | ✅/❌ | If fails: describe what happens |
| Clip Now button | ✅/❌ | Loading state? Error? |
| Voice recognition | ✅/❌ | Do you hear transcription? |
| Clip command | ✅/❌ | Brain recognizes it? |
| Search command | ✅/❌ | Brain recognizes "pull"? |
| Manual search | ✅/❌ | Results show? |

---

## 🔧 DEBUGGING COMMANDS

### **Check Brain Decider Locally**
```bash
python3 << 'EOF'
from backend.brain.decider import brain_decider

tests = [
    "clip that",
    "pull the tiktok of backflips",
    "find me some epic clips",
    "switch to facecam",
]

for cmd in tests:
    result = brain_decider.decide(cmd, ["Main", "Facecam"])
    print(f"Input: '{cmd}'")
    print(f"  Intent: {result.intent}")
    print(f"  Action: {result.action}")
    print(f"  Payload: {result.payload}")
    print()
EOF
```

### **Check API Connectivity**
```bash
# Auth check
curl -X GET http://localhost:8000/auth/me \
  -H "Content-Type: application/json" \
  -b "session_id=YOUR_SESSION_ID"

# Save clip endpoint
curl -X POST http://localhost:8000/api/clips/save-now \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search endpoint
curl -X POST http://localhost:8000/api/moment-finder/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 3}'
```

### **Check Logs**
```bash
# Backend logs (if running with --reload):
# Should see: "AI Decision:", "Brain Decision:", etc.

# Frontend console:
# Open DevTools F12 → Console
# Should see: "Transcribed: ...", error messages, etc.
```

---

## 🆘 EMERGENCY DIAGNOSTICS

**If everything is broken:**

1. **Verify servers are running:**
   ```bash
   # Backend should show: "Uvicorn running on http://0.0.0.0:8000"
   # Frontend should show: "VITE v... ready in 200ms"
   ```

2. **Check both logs for errors:**
   - Backend: Python exceptions?
   - Frontend: JavaScript errors in console?

3. **Test basic connectivity:**
   ```bash
   curl http://localhost:8000/health  # Should return 200
   curl http://localhost:5173         # Should return HTML
   ```

4. **Clear all caches:**
   ```javascript
   // DevTools Console:
   localStorage.clear()
   sessionStorage.clear()
   caches.keys().then(names => names.forEach(name => caches.delete(name)))
   location.reload()
   ```

5. **Restart both servers** from scratch

---

## 📝 WHAT TO REPORT

When reporting issues, include:
1. **Which test failed?** (Onboarding, Clip Now, Voice, Search, etc.)
2. **Exact error message?** (from console or toast)
3. **Backend logs** (last 20 lines with error)
4. **Network tab** (any failed requests?)
5. **Steps to reproduce** (what exactly did you do?)

---

**Once all tests pass, you're ready to launch! 🚀**

*Last updated: 2026-07-14*
