# 🧪 KAZUMI STREAMER DASHBOARD - COMPREHENSIVE TESTING GUIDE

## 📋 Table of Contents
1. [Pre-Testing Setup](#pre-testing-setup)
2. [Test 1: Groq AI - Text Chat](#test-1-groq-ai--text-chat)
3. [Test 2: Voice Commands](#test-2-voice-commands)
4. [Test 3: Dashboard Metrics](#test-3-dashboard-metrics)
5. [Test 4: OBS Integration](#test-4-obs-integration)
6. [Test 5: Sidebar Navigation](#test-5-sidebar-navigation)
7. [Test 6: Chat Drawer UI](#test-6-chat-drawer-ui)
8. [Test 7: Error Handling](#test-7-error-handling)
9. [Test 8: Real-Time Updates](#test-8-real-time-updates)
10. [Master Checklist](#master-checklist)
11. [Troubleshooting](#troubleshooting)

---

## 🔧 PRE-TESTING SETUP

### Requirements
- [ ] Node.js installed
- [ ] Project cloned and dependencies installed
- [ ] Groq API key obtained (free: https://console.groq.com/keys)
- [ ] OBS Studio installed (for full testing)
- [ ] Modern browser (Chrome recommended)

### Step 1: Add Groq API Key
```bash
# File: frontend/web/.env.local
# Create this file if it doesn't exist

NEXT_PUBLIC_GROQ_API_KEY=your_actual_groq_api_key_here
```

**How to get the key:**
1. Go to: https://console.groq.com/keys
2. Sign up (free account)
3. Create new API key
4. Copy the full key
5. Paste into .env.local

### Step 2: Start Development Server
```bash
cd frontend/web
npm run dev
```

Expected output:
```
> Compiled client and server successfully
> Ready in 1234ms
```

### Step 3: Open in Browser
- Go to: http://localhost:3000
- If redirected to login, sign in with your streamer account
- Should see dashboard with Kazumi avatar and "Ask Kazumi" button

**✅ Setup Complete!**

---

## 🤖 TEST 1: GROQ AI - TEXT CHAT

### Objective
Verify that Kazumee can receive text messages and respond with real AI from Groq.

### Test Steps

**Step 1: Open Chat Drawer**
- Location: Bottom-right corner
- Action: Click "Ask Kazumi" button
- Expected: Drawer slides in from right with smooth animation

**Step 2: Send First Message**
- Click in text input field (says "Ask Kazumee...")
- Type: `Hello Kazumee, how can you help me?`
- Press Enter or click Send button
- Expected:
  - Your message appears in purple gradient bubble
  - Message aligns to right side
  - Input field clears

**Step 3: Receive AI Response**
- Wait 1-3 seconds
- Expected:
  - Kazumee's response appears in blue/glass bubble
  - Aligns to left side
  - Contains real, intelligent answer (NOT fake/placeholder)
  - No error messages
  - Chat scrolls to show latest message

**Step 4: Multi-Turn Conversation**
- Ask: `What are the best settings for streaming on Twitch?`
- Expected: Real, helpful response
- Ask: `How do I increase my viewer engagement?`
- Expected: Different, relevant answer

**Step 5: Verify AI Quality**
- Responses should be:
  - ✅ Specific and helpful
  - ✅ Not generic or repetitive
  - ✅ Context-aware
  - ✅ Conversational tone
  - ✅ Proper length (1-2 paragraphs)

### ✅ Expected Results
- Text chat with Kazumee works perfectly
- All responses are from real Groq AI
- No errors in console
- Smooth animations
- Messages display correctly

### ❌ If Test Fails
**Issue: "Error: Failed to get response"**
- Solution: Check Groq API key in .env.local
- Verify key is valid: https://console.groq.com/keys
- Restart dev server after adding key

**Issue: Generic/Placeholder responses**
- Solution: Groq API key is invalid
- Get new key from console
- Update .env.local

**Issue: No response at all**
- Solution: Check browser network tab for API errors
- Verify internet connection
- Check Groq service status

### 📝 Test Notes
- Date tested: __________
- Issues found: __________
- Status: ✅ PASS / ❌ FAIL

---

## 🎤 TEST 2: VOICE COMMANDS

### Objective
Verify voice input works - speak to Kazumee and get real AI responses.

### Prerequisites
- [ ] Browser allows microphone access (first time may prompt)
- [ ] Microphone is working
- [ ] Quiet environment (minimal background noise)
- [ ] Test 1 (text chat) passed

### Test Steps

**Step 1: Grant Microphone Access**
- If prompted by browser: Click "Allow" for microphone
- If already allowed: Skip to Step 2

**Step 2: Open Chat Drawer**
- Click "Ask Kazumi" button (if not already open)

**Step 3: Test Voice Input**
- Look for 🎤 microphone button (right side of input)
- Click the 🎤 button
- Expected:
  - Button turns RED
  - Text shows "Listening..."
  - Ready to record

**Step 4: Speak Clearly**
- Speak: `"What are the best camera settings for gaming?"`
- Speak naturally, clear pronunciation
- Wait for speech to finish

**Step 5: Check Transcription**
- Expected:
  - Real-time text appears as you speak
  - Transcription shows in input field
  - Text is accurate (may have minor errors)

**Step 6: Submit and Get Response**
- Option A: Press Enter
- Option B: Wait for auto-submit after speech ends
- Option C: Click Send button
- Expected:
  - Message goes to Kazumee
  - Real AI response appears
  - Response is relevant to your question

**Step 7: Test Variations**
Try different voice queries:

| Query | Expected Response |
|-------|------------------|
| "Best OBS settings" | Specific technical answer |
| "How to grow my stream" | Actionable growth tips |
| "Tell me a joke" | Funny response |
| "What's CS2 best strategy" | Gaming advice |

### ✅ Expected Results
- Microphone captures voice clearly
- Real-time transcription works
- Text appears in input field
- AI responds to voice queries
- No mic permission errors
- Natural conversation flow

### ❌ If Test Fails
**Issue: "Microphone not detected"**
- Solution: Check browser microphone settings
- Try: Settings → Privacy → Microphone
- Allow microphone access for localhost

**Issue: Speech not transcribing**
- Solution: Check browser supports Web Speech API
- Use Chrome (best support)
- Speak louder and clearer
- Check for background noise

**Issue: Transcription text disappears**
- This is normal - happens between interim and final results
- Text reappears when complete

**Issue: Mic button doesn't turn red**
- Solution: Refresh page
- Check browser permissions
- Try different browser

### 🔍 Detailed Checklist
- [ ] Microphone button is clickable
- [ ] Button turns red when listening
- [ ] "Listening..." text appears
- [ ] Real-time transcription shows as speaking
- [ ] Transcription is mostly accurate
- [ ] Message sends after speaking
- [ ] AI responds within 3 seconds
- [ ] Response is relevant to query
- [ ] No console errors
- [ ] Can speak multiple times in one session

### 📝 Test Notes
- Date tested: __________
- Mic quality: Good / Fair / Poor
- Issues found: __________
- Status: ✅ PASS / ❌ FAIL

---

## 📊 TEST 3: DASHBOARD METRICS

### Objective
Verify all dashboard stats show real data (not dummy values).

### Prerequisites
- [ ] OBS Studio is running
- [ ] Stream is active OR configured
- [ ] Dashboard loads without errors

### Test Steps

**Step 1: Check Viewer Count**
- Location: Top-left area of dashboard
- Card: "Current Viewers"
- Expected:
  - Shows a real number (not "2,847" or "0")
  - Updates when viewers join/leave
  - Shows realistic count for your stream
  - Has percentage change (e.g., "+5%")

**Step 2: Check Stream Health**
- Card: "Stream Health"
- Expected:
  - Shows status (e.g., "Excellent", "Good", "Fair")
  - Shows percentage score (e.g., "95% score")
  - Changes based on FPS/bitrate quality
  - Updates in real-time

**Step 3: Check Clip Metrics**
- Card: "Auto Clips Today"
- Expected:
  - Shows real clip count
  - Updates when clips created
  - Shows manual clip count below
  - Not hardcoded to "0"

**Step 4: Check Mod Events**
- Card: "Mod Events"
- Expected:
  - Shows real mod action count
  - Shows auto-moderation percentage
  - Updates with stream activity
  - Shows actual numbers (not demo data)

**Step 5: Check Stream Pulse**
- Card: "Stream Pulse"
- Expected:
  - Shows quality score (0-100)
  - Shows trend direction (+/-)
  - Updates based on metrics
  - Reflects stream health

**Step 6: Verify Real-Time Updates**
- Change something in OBS (e.g., FPS)
- Wait 5 seconds
- Expected:
  - Dashboard metrics update automatically
  - No manual refresh needed
  - Changes reflect in health score
  - Smooth real-time updates

### ✅ Expected Results
- All metrics show real, current data
- No hardcoded demo numbers
- Values update in real-time
- Stats are logical and consistent
- No placeholder values shown

### ❌ If Test Fails
**Issue: All metrics show "0"**
- Solution: Start streaming
- Verify OBS connection
- Check `/api/dashboard` returns data

**Issue: Metrics don't update**
- Solution: Refresh page
- Check WebSocket connection
- Verify API endpoints working

**Issue: Unrealistic viewer count**
- Solution: Ensure actual stream running
- Check OBS metrics
- Verify data from correct streamer

### 📝 Test Notes
- Date tested: __________
- Stream status: Live / Offline / Test
- Issues found: __________
- Status: ✅ PASS / ❌ FAIL

---

## 🔌 TEST 4: OBS INTEGRATION

### Objective
Verify OBS Studio connection and real-time metrics display.

### Prerequisites
- [ ] OBS Studio installed and running
- [ ] OBS configured with your settings
- [ ] WebSocket connection enabled
- [ ] Streamer dashboard open

### Test Steps

**Step 1: Verify OBS Connection**
- Location: Top of dashboard near Kazumi avatar
- Look for: "Connected" or "Offline" status
- Expected: Shows "Connected" if OBS running

**Step 2: Check OBS Metrics Card**
- Card: "OBS Status" or similar
- Expected shows:
  - ✅ FPS (real value, not "60" dummy)
  - ✅ Bitrate (real kbps value)
  - ✅ Resolution (real 1920x1080, etc)
  - ✅ Current scene name
  - ✅ Status indicator

**Step 3: Change Scene in OBS**
- In OBS: Click different scene
- On dashboard: Watch for update
- Expected:
  - Dashboard shows new scene name
  - Updates within 1 second
  - Smooth transition

**Step 4: Check FPS Changes**
- In OBS: Monitor FPS in lower-left
- On dashboard: Check FPS display
- Expected:
  - Dashboard FPS matches OBS
  - Updates in real-time
  - Shows actual performance

**Step 5: Check Bitrate Changes**
- In OBS: Look at bitrate in lower stats
- On dashboard: Check bitrate value
- Expected:
  - Dashboard shows real bitrate
  - Updates as you stream
  - Shows current kbps/mbps

**Step 6: Test Disconnect**
- Close OBS
- Check dashboard status
- Expected:
  - Shows "Disconnected" or "Offline"
  - Graceful error message
  - Option to reconnect

**Step 7: Test Reconnect**
- Reopen OBS
- Dashboard should reconnect
- Expected:
  - Shows "Connected" again
  - Metrics resume updating
  - No manual action needed

### ✅ Expected Results
- OBS connection is stable
- Metrics show real data
- Real-time updates working
- Scene changes reflected
- Graceful error handling

### ❌ If Test Fails
**Issue: "Disconnected" always shown**
- Solution: Verify OBS WebSocket enabled
- Check port configuration
- Restart both OBS and dev server

**Issue: Metrics not updating**
- Solution: Check OBS connection status
- Verify network connectivity
- Reload page

**Issue: FPS/bitrate showing old values**
- Solution: Restart OBS connection
- Check for network lag
- Verify metrics feed

### 📝 Test Notes
- Date tested: __________
- OBS version: __________
- WebSocket status: Connected / Disconnected
- Issues found: __________
- Status: ✅ PASS / ❌ FAIL

---

## 📱 TEST 5: SIDEBAR NAVIGATION

### Objective
Verify sidebar collapse/expand and navigation works smoothly.

### Test Steps

**Step 1: Locate Sidebar**
- Left side of dashboard
- Contains: Logo, profile, navigation items
- Should see: Menu items with icons and text

**Step 2: Test Collapse**
- Click hamburger menu (≡) icon
- Expected:
  - Sidebar collapses smoothly
  - Shows only icons (not text)
  - Animation is smooth
  - Width reduces to ~70px

**Step 3: Click Navigation Item (Collapsed)**
- While sidebar is collapsed: Click an icon
- Expected:
  - Page navigates or section loads
  - Sidebar stays collapsed (unless needed to expand)
  - Content updates
  - No errors

**Step 4: Test Expand**
- Click hamburger menu (≡) again
- Expected:
  - Sidebar expands smoothly
  - Shows full text labels
  - Animation is smooth
  - Width returns to full

**Step 5: Test Full Navigation**
- Click different menu items
- Expected:
  - Each one navigates/loads correctly
  - No broken links
  - Icons highlight/show active state
  - Content loads quickly

### ✅ Expected Results
- Sidebar collapses/expands smoothly
- All navigation items work
- No console errors
- Active state shows correctly
- Responsive and fast

### 📝 Test Notes
- Date tested: __________
- Menu items tested: __________
- Issues found: __________
- Status: ✅ PASS / ❌ FAIL

---

## 💬 TEST 6: CHAT DRAWER UI

### Objective
Verify chat drawer animations, styling, and functionality.

### Test Steps

**Step 1: Open Chat Drawer**
- Click "Ask Kazumi" button
- Expected:
  - Drawer slides in from right
  - Smooth animation (not jerky)
  - Header shows Kazumee avatar + info
  - Input field ready to type

**Step 2: Test Message Styling**
- Send a message
- Expected:
  - Your message: Purple/gradient bubble, right-aligned
  - Kazumee message: Blue/glass bubble, left-aligned
  - Good contrast and readability
  - Emoji support works

**Step 3: Test Scrolling**
- Send multiple messages
- Expected:
  - Chat scrolls smoothly
  - Auto-scrolls to newest message
  - No lag or jank

**Step 4: Test Input Field**
- Expected:
  - Placeholder text: "Ask Kazumee..."
  - Cursor visible and responsive
  - Text appears as you type
  - Enter key works to send

**Step 5: Test Minimize**
- Click X button in header
- Expected:
  - Drawer closes/minimizes
  - "Ask Kazumi" button reappears
  - Smooth animation

**Step 6: Test Reopen**
- Click "Ask Kazumi" button
- Expected:
  - Drawer opens again
  - Previous messages still there (memory works)
  - Same smooth animation

**Step 7: Test Send Variations**
- Press Enter: Message sends
- Click Send button: Message sends
- Click while mic listening: Should not send

### ✅ Expected Results
- All animations are smooth
- Messages style correctly
- Drawer works reliably
- Memory persists
- No visual glitches

### 📝 Test Notes
- Date tested: __________
- Browser: __________
- Screen resolution: __________
- Issues found: __________
- Status: ✅ PASS / ❌ FAIL

---

## ❌ TEST 7: ERROR HANDLING

### Objective
Verify app handles errors gracefully without crashing.

### Test Steps

**Step 1: Test Invalid Groq Key**
- Edit .env.local: Set key to "invalid_key_12345"
- Restart dev server
- Open chat
- Try to send message
- Expected:
  - Clear error message appears
  - Suggests checking API key
  - App doesn't crash
  - Can close error and retry

**Step 2: Test Network Disconnect**
- Open DevTools (F12) → Network tab
- Throttle to "Offline"
- Try to send message
- Expected:
  - Friendly error message
  - Suggests checking connection
  - App remains stable

**Step 3: Test OBS Disconnect**
- Close OBS
- Watch dashboard
- Expected:
  - Shows "Disconnected" status
  - Doesn't crash
  - Can still use chat
  - Graceful degradation

**Step 4: Test API Timeout**
- With Offline mode: Try to load dashboard
- Expected:
  - Timeout message appears
  - Retry option available
  - No infinite loading

### ✅ Expected Results
- All errors handled gracefully
- No app crashes
- User-friendly error messages
- Clear next steps provided
- Recovery possible

### 📝 Test Notes
- Date tested: __________
- Error scenarios tested: __________
- Issues found: __________
- Status: ✅ PASS / ❌ FAIL

---

## ⚡ TEST 8: REAL-TIME UPDATES

### Objective
Verify dashboard updates in real-time without page refresh.

### Test Steps

**Step 1: Monitor Viewer Count**
- Have viewers join your stream
- Watch viewer count card
- Expected: Count increases in real-time (1-2 sec delay)

**Step 2: Monitor Stream Health**
- Change OBS settings (FPS, bitrate)
- Watch health score
- Expected: Updates within 2-3 seconds

**Step 3: Monitor Chat Events**
- Send chat messages
- Watch event feed
- Expected: Messages appear immediately

**Step 4: Monitor Clip Counter**
- Create a clip in OBS or via button
- Watch clip counter
- Expected: Counter increments immediately

**Step 5: Monitor SuperChat**
- Simulate or receive super chat
- Watch dashboard update
- Expected: Updates immediately

### ✅ Expected Results
- All metrics update in real-time
- No page refresh needed
- Updates are smooth
- Delays are acceptable (<3 seconds)
- WebSocket connection stable

### 📝 Test Notes
- Date tested: __________
- Real-time features tested: __________
- Average update latency: __________ seconds
- Issues found: __________
- Status: ✅ PASS / ❌ FAIL

---

## ✅ MASTER CHECKLIST

### AI & Voice (High Priority)
- [ ] Text chat sends and receives
- [ ] Groq API responds with real answers
- [ ] Microphone records voice
- [ ] Voice transcription shows in real-time
- [ ] Voice transcription is accurate
- [ ] AI understands voice queries
- [ ] Error handling for Groq failures
- [ ] Multiple conversation turns work

### Dashboard Metrics (High Priority)
- [ ] Viewer count shows real number
- [ ] Stream health shows real status
- [ ] Clip counter shows real count
- [ ] Mod events shows real events
- [ ] Stream pulse shows real score
- [ ] All metrics update in real-time
- [ ] No hardcoded demo data
- [ ] Fallback values when offline

### OBS Integration (High Priority)
- [ ] OBS connection shows status
- [ ] FPS shows real value
- [ ] Bitrate shows real value
- [ ] Resolution shows correct
- [ ] Scene switching reflected
- [ ] Metrics update in real-time
- [ ] Reconnection works smoothly
- [ ] Error handling for disconnects

### UI/UX (Medium Priority)
- [ ] Sidebar collapses smoothly
- [ ] Chat drawer animates properly
- [ ] All buttons are clickable
- [ ] Text is readable
- [ ] Colors are consistent
- [ ] Layout is responsive
- [ ] No visual glitches
- [ ] Smooth scroll performance

### Error Handling (Medium Priority)
- [ ] API errors show friendly messages
- [ ] Network errors are handled
- [ ] Invalid inputs prevented
- [ ] App doesn't crash on errors
- [ ] Recovery options available
- [ ] Console has no critical errors
- [ ] User knows what to do when error occurs

### Performance (Low Priority)
- [ ] Chat loads quickly
- [ ] Dashboard loads quickly
- [ ] Sidebar toggles smoothly
- [ ] No lag during typing
- [ ] Smooth animations
- [ ] No memory leaks
- [ ] CPU usage reasonable

---

## 🆘 TROUBLESHOOTING

### Groq AI Issues

| Problem | Solution |
|---------|----------|
| "API key error" | Check .env.local has correct key from https://console.groq.com/keys |
| No AI response | Restart dev server after adding key |
| Generic responses | Verify Groq API key is valid (not free trial expired) |
| Timeout error | Check internet connection, Groq servers status |
| Rate limited | Groq free tier has limits, wait a few seconds before retrying |

### Voice Issues

| Problem | Solution |
|---------|----------|
| Mic not working | Check browser permissions: Settings → Privacy → Microphone |
| Speech not recognized | Speak clearly, check for background noise, try Chrome |
| Transcription incorrect | Speak slower, use clearer pronunciation |
| Mic button doesn't turn red | Refresh page, check browser version |
| No interim transcription | This is normal, text shows after speaking ends |

### Dashboard Issues

| Problem | Solution |
|---------|----------|
| All metrics show "0" | Start stream, check API endpoints |
| Metrics don't update | Refresh page, check WebSocket connection |
| OBS disconnected | Verify OBS WebSocket enabled, restart OBS |
| Blank dashboard | Reload page, check API response |
| Slow loading | Check network speed, close other tabs |

### Browser Compatibility

| Browser | Status | Notes |
|---------|--------|-------|
| Chrome | ✅ Best | Full support for voice and WebSocket |
| Firefox | ✅ Good | Works but may have voice lag |
| Safari | ⚠️ Partial | Voice may require permissions |
| Edge | ✅ Good | Chromium-based, works well |
| Mobile | ⚠️ Limited | Not optimized for mobile yet |

---

## 📞 GETTING HELP

If tests fail:
1. Check troubleshooting table above
2. Verify setup steps were completed
3. Check browser console for errors (F12)
4. Try different browser
5. Restart dev server
6. Clear browser cache (Ctrl+Shift+Delete)

**Document all findings and errors found!**

---

## 🎯 SUCCESS CRITERIA

All tests pass when:
- ✅ All text chats work with real Groq AI
- ✅ Voice input captures and transcribes accurately
- ✅ All dashboard metrics show real, current data
- ✅ OBS integration shows live metrics
- ✅ UI is smooth and responsive
- ✅ Error handling is graceful
- ✅ Real-time updates work smoothly
- ✅ No console errors or crashes

**When all pass: System is production-ready!** 🚀

---

**Last Updated:** $(date)
**Test Status:** Ready to Begin ✅
**Tester Name:** __________
**Testing Date:** __________
