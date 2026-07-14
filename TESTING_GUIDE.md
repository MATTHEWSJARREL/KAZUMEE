# 🧪 Complete Testing Guide - Kazumi Streamer Dashboard

## ✨ Before You Test

1. **Restart dev server:**
   ```bash
   npm run dev
   ```

2. **Add your Groq API key** to `frontend/web/.env.local`:
   ```
   NEXT_PUBLIC_GROQ_API_KEY=your_key_here
   ```

3. **Make sure OBS is running** (for real metrics)

---

## 🎯 Test #1: Chat with Kazumee (Text + AI)

### Steps:
1. Click **"Ask Kazumi"** button (bottom-right)
2. Type: **"What's the best overlay for gaming?"**
3. Press Enter or click Send

### Expected Results:
- ✅ Chat drawer slides in smoothly
- ✅ Message appears in purple bubble
- ✅ Kazumee responds with real AI answer (from Groq)
- ✅ Response appears in blue/purple bubble
- ✅ No error messages

### If it fails:
- Check Groq API key in `.env.local`
- Check browser console for errors
- Make sure API key is valid (https://console.groq.com/keys)

---

## 🎤 Test #2: Voice Commands (Microphone)

### Steps:
1. Click **"Ask Kazumi"** button
2. Click **🎤 microphone button** (right side of input)
3. Speak clearly: **"What are the best CS2 smokes?"**
4. Wait for transcription to finish
5. Press Send or wait for auto-send

### Expected Results:
- ✅ Microphone button turns red (listening)
- ✅ Your speech shows as text in real-time
- ✅ Text appears in input field
- ✅ Click send to submit
- ✅ Get AI response about CS2 smokes
- ✅ Response includes helpful info

### If it fails:
- Check browser allows microphone access
- Try different browser (Chrome > Firefox > Safari)
- Speak clearly and louder
- Check console for speech recognition errors

### Test Variations:
- **Gaming Help**: "What's the best strategy for Valorant attack round?"
- **Streaming Help**: "How do I set up a good stream layout?"
- **General**: "Tell me a joke"
- **Long question**: "What are the key things I should do at the start of my stream?"

---

## 📊 Test #3: Dashboard Metrics (Real Data)

### Setup:
1. Go to streamer dashboard
2. Check that OBS is connected

### Test Viewer Count:
- [ ] "Current Viewers" shows a number
- [ ] Number updates in real-time as viewers join/leave
- [ ] Shows realistic number (not "2,847" dummy)

### Test Stream Health:
- [ ] Shows health status
- [ ] Shows percentage score
- [ ] Updates based on FPS, bitrate, etc.

### Test Clip Metrics:
- [ ] "Auto Clips Today" shows real count
- [ ] Increments when you create a clip
- [ ] Shows manual clip count below

### Test Stream Pulse:
- [ ] Shows score (0-100)
- [ ] Shows trend (+/- direction)
- [ ] Updates based on stream quality

### If metrics don't update:
- Make sure you're actually streaming
- Check OBS connection status
- Verify `/api/dashboard` returns real data
- Check network tab in DevTools

---

## 🔌 Test #4: OBS Integration

### Steps:
1. Open OBS Studio
2. Start a test stream (or just prepare stream)
3. Check dashboard shows OBS status

### Expected Results:
- ✅ Shows "Connected" or "Streaming"
- ✅ Shows real FPS (not hardcoded)
- ✅ Shows real bitrate
- ✅ Shows real resolution
- ✅ Updates in real-time

### Test Scene Switching:
- [ ] Change scene in OBS
- [ ] Dashboard updates immediately
- [ ] Shows current scene name

### If OBS doesn't connect:
- Make sure WebSocket server is running
- Check OBS connection settings
- Verify port 4444 (or configured port)

---

## 💬 Test #5: SuperChat Integration

### Steps:
1. (Simulate or receive actual super chat)
2. Check dashboard shows notification
3. Click to see sorted super chats

### Expected Results:
- ✅ Shows super chat notification
- ✅ Displays sender name
- ✅ Shows message content
- ✅ Displays amount
- ✅ Can approve/respond

### If super chats don't show:
- Check `/api/superchat/sorted` is working
- Verify backend connection
- Check firewall/network

---

## 🎮 Test #6: Sidebar Functionality

### Steps:
1. Check sidebar on left
2. Test collapse/expand
3. Click navigation items

### Expected Results:
- ✅ Hamburger menu (≡) toggles sidebar
- ✅ Sidebar shows just icons when collapsed
- ✅ Clicking icons navigates without expanding
- ✅ Smooth animations

---

## 📱 Test #7: Chat Drawer UI

### Steps:
1. Open chat drawer
2. Send messages back and forth
3. Close and reopen

### Expected Results:
- ✅ Drawer slides in from right
- ✅ Messages show with correct styling
- ✅ User messages: purple/gradient
- ✅ Kazumee messages: blue/glass effect
- ✅ Smooth animations
- ✅ Scroll works smoothly
- ✅ Close (X) minimizes properly
- ✅ "Ask Kazumi" button reappears

---

## ❌ Test #8: Error Handling

### Test Groq API Error:
1. Remove/invalidate API key
2. Try to send message
3. Should see error message

### Expected Results:
- ✅ Clear error message shown
- ✅ Suggests adding API key
- ✅ Doesn't crash app

### Test Network Error:
1. Disable internet
2. Try to send message
3. Should handle gracefully

### Test OBS Disconnection:
1. Close OBS
2. Dashboard should show "Not connected"
3. Auto-reconnect when OBS comes back

---

## 📋 Full Test Checklist

### AI & Voice (High Priority)
- [ ] Text chat with AI works
- [ ] Voice input works (microphone)
- [ ] Real-time transcription shows
- [ ] AI responses are intelligent
- [ ] Error messages are helpful

### Dashboard (High Priority)
- [ ] Viewer count shows real number
- [ ] Stream health updates
- [ ] Clip counter works
- [ ] All metrics use real data
- [ ] No hardcoded demo numbers

### UI/UX (Medium Priority)
- [ ] Sidebar collapses smoothly
- [ ] Chat drawer animates well
- [ ] All buttons work
- [ ] No visual glitches
- [ ] Responsive on different screen sizes

### Error Handling (Medium Priority)
- [ ] Graceful error messages
- [ ] App doesn't crash on errors
- [ ] Network errors handled
- [ ] Offline states handled

### OBS Integration (High Priority)
- [ ] Real-time connection status
- [ ] FPS/bitrate show real values
- [ ] Scene switching reflected
- [ ] Resolution shows correct
- [ ] Auto-reconnect works

### Performance (Low Priority)
- [ ] No console errors
- [ ] Smooth scrolling
- [ ] Fast response times
- [ ] Chat loads quickly

---

## 🚀 When All Tests Pass

1. ✅ All features working
2. ✅ All data is real (no dummy)
3. ✅ Error handling works
4. ✅ UI is smooth and responsive

**READY FOR PRODUCTION!**

---

## 📞 Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| AI not responding | Check Groq API key in `.env.local` |
| Microphone not working | Check browser microphone permissions |
| OBS not connected | Check WebSocket server running |
| No viewer count | Make sure stream is live |
| Sidebar not collapsing | Clear cache, refresh page |
| Chat drawer jittery | Check browser performance |

---

## 📸 Screenshots to Verify

Take screenshots to verify:
1. Kazumee chat drawer with message
2. Voice transcription in real-time
3. Dashboard with real metrics
4. Sidebar collapsed with hamburger
5. OBS metrics showing real data

**Start testing now!** 🎯
