# 🎯 KAZUMEE ARCHITECTURE EXPLAINED

## WHAT KAZUMEE IS

**Kazumee is an AI-powered streaming co-pilot** that helps streamers:

1. **Control their stream** via voice commands and OBS integration
2. **Automate clip creation** - AI detects the best moments and exports them
3. **Moderate chat** - AI-powered content filtering and moderation
4. **Engage viewers** - AI recaps, highlights, and chat features
5. **Manage commands** - Viewers can request actions (scene changes, sounds, etc.)
6. **Monitor health** - Real-time stream quality and performance monitoring
7. **Grow their community** - Viral content detection and export to TikTok/Shorts/Reels

**For Viewers:** AI-powered watch experience with recaps, highlights, and interactive features

---

## COMPLETE USER JOURNEYS

### 🎬 STREAMER JOURNEY

```
1. LANDING PAGE (/)
   └─ Visit Kazumee website
   └─ See features: Voice control, Auto-clipping, Moderation, Viewer Companion
   └─ Click "Start Free" button

2. REGISTRATION (/auth)
   └─ Enter email, password
   └─ Select "Streamer" role
   └─ Click "Create Account"
   └─ Backend creates User + Streamer account

3. ONBOARDING (/onboarding)
   Step 1: Basic Setup
   └─ Display name (e.g., "Cool Streamer")
   └─ Platform selection (Twitch, YouTube, Both)

   Step 2: OBS Connection
   └─ Download OBS (if needed)
   └─ Enable WebSocket server
   └─ Enter WebSocket password
   └─ Test connection (verifies OBS is running)

   Step 3: Voice Setup
   └─ 10-second voice recording
   └─ Kazumi learns your voice for security

   Step 4: Scene Aliases
   └─ Map OBS scenes to roles (Main, BRB, Facecam)
   └─ Helps voice commands work correctly

   Completion
   └─ Click "Go to Dashboard"
   └─ Dashboard flag: onboarding_complete = true

4. STREAMER DASHBOARD (/dashboard)
   The full command center with:

   TOP BAR
   └─ OBS Status (connected/disconnected)
   └─ Stream health score (Optimal/Warning/Critical)
   └─ CPU, Memory, Bitrate, Dropped Frames

   LEFT SIDEBAR
   └─ Dashboard (home)
   └─ Stream Health (detailed metrics)
   └─ Clips Library (approval panel)
   └─ Command Queue (viewer requests)
   └─ Moderation (chat filtering)
   └─ Analytics (engagement metrics)
   └─ ML Training (teach Kazumi)
   └─ Voice Control (settings)
   └─ Settings (integrations)

   MAIN CONTENT AREA
   └─ Stream KPIs (viewers, chat rate, engagement)
   └─ Command center (execute/reject viewer commands)
   └─ Live events feed (clips created, follows, raids, etc.)
   └─ AI approval dashboard (review AI suggestions)
   └─ OBS control panel (switch scenes, mute mic, etc.)
   └─ Moment finder (search for highlights)
   └─ Post-stream report (auto-generated summary)

5. STREAMING LIVE
   While streaming:
   └─ Voice commands: "Kazumi, switch to chat cam"
   └─ Auto-clipping: AI detects epic moments
   └─ Moderation: Chat filtered in real-time
   └─ Commands: Viewers request actions (scene, sound, etc.)
   └─ Dashboard: Live metrics update in real-time

6. POST-STREAM
   After stream ends:
   └─ Post-Stream Report: AI-generated summary
   └─ Auto-clips: View all clips created
   └─ Engagement metrics: See what worked
   └─ Export options: TikTok, Shorts, Reels

7. RETURNING STREAMER
   Next time they log in:
   └─ Visit /
   └─ System detects: role = "streamer" + onboarding_complete = true
   └─ Redirects to /dashboard automatically
   └─ Dashboard loads with live data
```

### 👁️ VIEWER JOURNEY

```
1. LANDING PAGE (/)
   └─ Visit Kazumee website
   └─ Scroll to "For Viewers" section
   └─ Click "Watch as a Viewer" button

2. REGISTRATION (/auth)
   └─ Enter email, password
   └─ "Viewer" role selected by default
   └─ Click "Create Account"
   └─ Backend creates User + Viewer account

3. VIEWER PAGE (/viewer)
   └─ See list of streamers
   └─ Select a streamer to watch
   └─ Get AI-powered recap of stream

4. VIEWER EXPERIENCE
   While watching:
   └─ AI recap: "Here's what happened"
   └─ Highlights: Jump to epic moments
   └─ Clip timeline: See all AI-detected highlights
   └─ Chat enhance: Better emoji, clearer messages
   └─ Request clips: "Clip that moment!"
   └─ Vote on scenes: "Switch to camera"
   └─ Catch up: "What did I miss?" → AI recap

5. RETURNING VIEWER
   Next time they log in:
   └─ Visit any page
   └─ System detects: role = "viewer"
   └─ Redirects to /viewer automatically
```

---

## ROUTING ARCHITECTURE (CORRECTED)

### Routes Map

```
/                          → HomePage (Landing or Smart Redirect)
├─ If NOT logged in        → Show LandingPage
├─ If role = streamer      → Redirect to /dashboard
└─ If role = viewer        → Redirect to /viewer

/auth                       → AuthPage (Login & Registration)
├─ Registration modes:
│  ├─ Streamer → Redirect to /onboarding
│  └─ Viewer → Redirect to /viewer
└─ Login modes:
   ├─ Streamer → Redirect to /
   └─ Viewer → Redirect to /viewer

/onboarding                 → OnboardingPage (4-step setup)
├─ Step 1: Display name + platform
├─ Step 2: OBS WebSocket connection
├─ Step 3: Voice fingerprint (10 sec recording)
├─ Step 4: Scene aliases mapping
└─ Complete: Redirect to /dashboard

/dashboard                  → KazumiDashboard (STREAMER ONLY)
├─ Protected by RoleGuard (requires auth + streamer role)
├─ Components:
│  ├─ StreamObserver: Real-time stream data
│  ├─ CommandCenter: Process viewer requests
│  ├─ ClipManager: Approve/reject AI clips
│  ├─ Moderation: Chat filtering
│  ├─ Analytics: Engagement metrics
│  ├─ OBSControl: Switch scenes, mute, etc.
│  ├─ MomentFinder: Search for highlights
│  └─ PostStreamReport: Auto-generated summary
└─ Real-time updates via WebSocket

/viewer                     → ViewerDashboard (VIEWER ONLY)
├─ Protected by RoleGuard (requires auth + viewer role)
├─ Shows:
│  ├─ List of streamers
│  ├─ Streamer's current stream
│  ├─ AI recap of stream
│  ├─ Highlights timeline
│  └─ Viewer engagement features
└─ Real-time updates via WebSocket

/stream-health             → Detailed health metrics (STREAMER ONLY)
/clips                      → Clip library & approval (STREAMER ONLY)
/moderation                 → Chat moderation panel (STREAMER ONLY)
/commands                   → Command queue (STREAMER ONLY)
/analytics                  → Engagement analytics (STREAMER ONLY)
/ml-training                → ML training interface (STREAMER ONLY)
/voice                      → Voice agent settings (STREAMER ONLY)
/settings                   → Integrations & settings (STREAMER ONLY)
```

---

## FILE STRUCTURE (FIXED)

```
frontend/web/src/app/
├── page.jsx                      ← HOME PAGE (Landing + Smart Redirect)
├── root.tsx                      ← Root layout with RoleGuard + OnboardingBanner
├── global.css
│
├── auth/
│   └── page.jsx                  ← Auth page (Login & Registration)
├── auth.css
│
├── onboarding/
│   └── page.tsx                  ← Onboarding flow (4 steps)
│
├── dashboard/
│   └── page.jsx                  ← KazumiDashboard (Full streamer dashboard)
│
└── viewer/
    └── page.jsx                  ← ViewerDashboard (Viewer experience)
```

---

## COMPONENT HIERARCHY

### HomePage (/page.jsx)
```
HomePage
├─ Check auth token
├─ If no token → Show LandingPage
├─ If streamer → Navigate to /dashboard
├─ If viewer → Navigate to /viewer
└─ If loading → Show spinner
```

### KazumiDashboard (/dashboard/page.jsx)
```
KazumiDashboard
├─ Real-time data polling (5 sec interval)
├─ WebSocket connection for live updates
├─ Sidebar with navigation
│  ├─ Dashboard (home)
│  ├─ Stream Health
│  ├─ Clips Library
│  ├─ Command Queue
│  ├─ Moderation
│  ├─ Analytics
│  ├─ ML Training
│  ├─ Voice Control
│  └─ Settings
├─ Main content (tabs based on nav)
│  ├─ Stream KPIs
│  ├─ Command Center
│  ├─ Live Events
│  ├─ AI Approval
│  ├─ OBS Control
│  ├─ Moment Finder
│  ├─ Post Stream Report
│  └─ Source/Camera Control
├─ Panic Mode button
├─ Voice listener (when enabled)
└─ Clip now button (Ctrl+Shift+C)
```

---

## BACKEND ENDPOINTS (By Feature)

### Authentication
```
POST /auth/register                  → Create user account
POST /auth/login                     → Login & get token
GET  /auth/me                        → Get current user info
POST /auth/role                      → Switch roles
GET  /auth/streamers                 → Get available streamers
POST /auth/active-streamer           → Set active streamer context
```

### Onboarding
```
POST /api/streamer/onboarding/complete      → Mark setup done
PUT  /api/streamer/settings                 → Save settings (OBS pwd, display name)
POST /api/streamer/scene-aliases            → Save scene mappings
POST /api/voice-agent/fingerprint/record    → Save voice sample
POST /api/obs/test-connection               → Test OBS WebSocket
```

### Dashboard
```
GET  /api/dashboard                  → Get dashboard data (KPIs, activity, etc.)
GET  /api/stream-health              → Detailed stream metrics
GET  /events/log                     → Get event log (commands, clips, etc.)
```

### Clips
```
GET  /api/clips                      → Get clips list
POST /api/clips/create               → Create new clip
POST /api/clips/{id}/approve         → Approve clip for export
POST /api/clips/{id}/export          → Export to platform (TikTok, Shorts, etc.)
```

### Commands
```
GET  /api/commands                   → Get command queue
POST /api/commands/process           → Process viewer command
POST /api/commands/{id}/execute      → Execute queued command
POST /api/commands/{id}/reject       → Reject command
```

### Viewer
```
GET  /api/viewer/dashboard           → Get viewer-specific content
POST /api/viewer/vote                → Vote on scene change
POST /api/viewer/redeem              → Redeem credits for action
POST /api/viewer/clip-request        → Request clip creation
```

---

## DATA FLOW

### User Registration

```
User enters email/password on /auth
    ↓
Frontend validates (email, password 8+)
    ↓
POST /auth/register { email, password, role }
    ↓
Backend:
  ├─ Hash password (PBKDF2-SHA256)
  ├─ Create User record
  ├─ Create Streamer/Viewer record
  └─ Generate auth token
    ↓
Frontend receives token + user data
    ↓
Frontend stores token in localStorage
    ↓
Redirect based on role:
  ├─ Streamer → /onboarding
  └─ Viewer → /viewer
```

### Streaming Live

```
OBS sends events via WebSocket
    ↓
Backend StreamObserver processes:
  ├─ Chat messages
  ├─ Donations, raids, follows
  └─ Stream metrics (viewers, bitrate, etc.)
    ↓
Backend runs AI analysis:
  ├─ Moment detection (Is this clipworthy?)
  ├─ Sentiment analysis (Positive/negative chat)
  └─ Content classification (Gaming, talk, etc.)
    ↓
If moment detected:
  ├─ Create Clip record in database
  ├─ Extract clip file from replay buffer
  └─ Send WebSocket event to dashboard
    ↓
Dashboard updates in real-time:
  ├─ New clip appears in "AI Approval" panel
  ├─ Streamer can approve/reject
  └─ Export to social media (TikTok, YouTube Shorts, Instagram Reels)
```

---

## WHAT EACH PAGE DOES

### / (HomePage)
- **Not logged in**: Shows beautiful landing page with features, pricing, CTA
- **Logged in as streamer**: Redirects to /dashboard
- **Logged in as viewer**: Redirects to /viewer
- **Purpose**: Entry point and smart routing hub

### /auth (AuthPage)
- **Sign up as streamer**: Email → /onboarding
- **Sign up as viewer**: Email → /viewer
- **Sign in**: Takes you to appropriate place based on role
- **Purpose**: Central authentication hub

### /onboarding (OnboardingPage)
- **Step 1**: Create streamer profile (display name, platform)
- **Step 2**: Connect OBS via WebSocket
- **Step 3**: Record voice sample (Kazumi learns your voice)
- **Step 4**: Map OBS scenes to aliases (Main, BRB, Facecam)
- **Purpose**: Get streamer fully set up and ready to use Kazumee

### /dashboard (KazumiDashboard)
- **Full streaming command center**
- **Real-time metrics**: Viewers, health, chat rate
- **Command queue**: Process viewer requests
- **Clip library**: Review and export AI-detected clips
- **Moderation**: Filter/block chat messages
- **Analytics**: Engagement insights
- **Voice control**: Enable AI voice listening
- **OBS control**: Switch scenes, mute mic, etc.
- **Purpose**: Complete streaming experience with AI assistance

### /viewer (ViewerDashboard)
- **Browse streamers**: See who's live
- **Watch with AI assist**: Recaps, highlights, timeline
- **Engage**: Vote on scenes, request clips, interact with chat
- **Purpose**: Enhanced viewing experience with AI features

---

## KEY TECHNOLOGIES

### Frontend
- **React Router**: Client-side routing
- **Tailwind CSS**: Styling
- **Sonner**: Toast notifications
- **WebSocket**: Real-time updates
- **localStorage**: Token persistence

### Backend
- **FastAPI**: Python web framework
- **SQLAlchemy**: ORM for database
- **WebSocket**: Real-time server push
- **Groq API**: LLM for AI features
- **OBS WebSocket**: Stream control

### Integrations
- **Twitch OAuth**: Login & stream access
- **YouTube API**: Stream management
- **TikTok API**: Content export
- **OBS WebSocket**: Scene/source control

---

## SECURITY LAYERS

1. **Authentication**: Token-based (localStorage + header)
2. **Authorization**: RoleGuard (streamer vs viewer routes)
3. **Validation**: Email/password checks on frontend & backend
4. **Rate limiting**: 10 req/min on auth endpoints
5. **Password hashing**: PBKDF2-SHA256 with 120k iterations
6. **Session timeout**: 30 days (configurable)
7. **CORS**: Configured per environment

---

## PERFORMANCE

### Real-time Updates
- Dashboard data refreshes every 5 seconds
- WebSocket for instant notifications
- Event streaming for live activity
- Optimized queries with indexes

### Caching
- Dashboard data cached in localStorage
- React Query for API response caching
- OBS scene list cached for 5 seconds

### Optimization
- Lazy loading components
- Code splitting by route
- Image optimization
- CSS minification

---

## SUMMARY

Kazumee is a **complete streaming automation platform** that:

✅ **Helps streamers** control their stream with voice, auto-create clips, moderate chat, and grow
✅ **Helps viewers** watch with AI recaps, highlights, and interactive features
✅ **Uses AI** to detect moments, moderate chat, and generate content
✅ **Integrates** with Twitch, YouTube, TikTok, OBS, and more
✅ **Real-time** with WebSocket for instant updates
✅ **Scales** with FastAPI async backend

---

**The architecture is now CLEAN, ORGANIZED, and READY! 🎉**
