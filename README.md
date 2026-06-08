# Kazumi - AI Stream Assistant

Kazumi is a SaaS-first AI stream assistant with a local agent for OBS control.
It supports streamer + viewer roles, safe action policies, and cross-platform
ingestion (starting with Twitch + YouTube).

## Architecture

### Backend Structure
```
backend/
+-- main.py              # FastAPI entrypoint
+-- config/              # Configuration files
+-- core/                # Core utilities (logger, ws, events)
+-- brain/               # AI decision making
+-- director/            # OBS control and health monitoring
+-- researcher/          # Clip search and vector database
+-- commands/            # Command processing
+-- api/                 # REST API routes
+-- database/            # Database models and connections
+-- alembic/             # Database migrations
+-- data/                # Static data (clips, vector db)
```

### Key Components
- **Brain**: Single AI decision engine (Groq-based)
- **Director**: Single OBS controller and health monitoring
- **Researcher**: Single clip search service (ChromaDB + embeddings)
- **Commands**: Unified command processing pipeline
- **Auth**: Email/password with role selection (streamer / viewer)
- **Policy Engine**: Enforces viewer safety (allow / approve / deny)
- **Ingestion**: Unified event schema for Twitch + YouTube (Phase 2)

## Setup

1. Create virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and OBS settings
   ```

4. Initialize DB (first run):
   ```bash
   py -3.11 backend/init_db.py
   py -3.11 -m alembic upgrade head
   ```

5. Start the application:
   ```bash
   ./scripts/start.sh
   ```

## Auth & Roles
- Visit `/auth` to create an account.
- Choose **Streamer** or **Viewer**.
- Viewers must select an **Active Streamer** to sync lore, clips, and voting.
- Streamer + viewer roles are enforced with route guards.

## Viewer Safety Policy
Viewer actions are evaluated by a policy engine:
- **allow**: chat, lore, clip requests, voting
- **approve**: scene switches, recording/mic control (queued)
- **deny**: start/stop stream, panic, restart

## Event Ingestion
Use `/api/ingest` with the normalized schema:
```json
{
  "platform": "twitch",
  "event_type": "chat_message",
  "event_id": "optional-id",
  "user_id": "123",
  "username": "viewer123",
  "message": "clip that"
}
```

## Roadmap (Product Vision)
**Phase 1: Foundation (multi-tenant + auth)**
- Add streamer_id to all key DB models
- Auth + role enforcement (streamer / viewer)
- Endpoints require streamer context

**Phase 2: Cross-platform ingestion**
- Normalize Twitch + YouTube (later TikTok/Kick)
- Store events + route to brain/approval queue

**Phase 3: Command policy engine**
- Action safety matrix (allow / approve / deny)
- Admin UI per streamer
- Auto-approve based on tier + confidence

**Phase 4: SaaS Brain + Local Agent**
- Local OBS agent executes signed commands
- SaaS brain issues decisions

**Phase 5: Analytics + Monetization**
- Streamer analytics + billing
- Premium viewer perks

## Roadmap (Implementation Phases in This Repo)
**Phase 1**
- Email/password auth + role selection
- Viewer chooses active streamer
- streamer_id scoping in core endpoints

**Phase 2**
- Policy engine enforcement
- Unified event ingestion schema
- Approval queue paths

**Phase 2.5**
- Event deduplication with event_id hashing
- YouTube poll cursor tracking (nextPageToken)
- Safer ingestion storage helpers

**Phase 3**
- Twitch/YouTube OAuth flows
- Encrypted token storage
- Auto ingestion loop
- Live events feed (SSE)

**Phase 3.6**
- Streamer-configurable action policy UI
- Backend policy overrides per streamer

**Phase 4**
- Signed command requests for local agent
- Agent command queue and ACK flow
- Safe local agent skeleton (no-op by default)

**Phase 5 (Core Analytics)**
- Backend analytics now aggregates DB events, commands, and clips
- Ops metrics: approvals, pending actions, clip status
- Platform mix breakdown for event traffic

**Phase 6 (Moment Finder)**
- Cross-platform clip search links (Twitch, YouTube, TikTok, Kick)
- Backend `/api/moment-finder/search` endpoint
- Streamer UI panel in dashboard
- Platform filter toggles + query presets
- Saved link collection (localStorage)

**Phase 7 (Auto-Clip MVP)**
- Auto-clip trigger on chat spikes
- Replay buffer save on highlight detection

**Phase 7.1 (Taste Learning)**
- Streamer taste profile updated on clip approvals/rejections
- Clip quality score adjusted based on learned tags
- Automatic tag extraction from clip text
- Taste profile surfaced in analytics

**Phase 8 (Short-Form Export MVP)**
- Export job via local agent (TikTok/Shorts/Reels)
- ffmpeg-based 9:16 export (local)

**Phase 9 (Setup Wizard)**
- Streamer setup wizard (OAuth + OBS + Agent)

## OAuth (Phase 3.1)
Set these environment variables:
```
PUBLIC_BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=http://localhost:5173
TWITCH_CLIENT_ID=...
TWITCH_CLIENT_SECRET=...
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
TWITCH_WEBHOOK_SECRET=...
TOKEN_ENCRYPTION_KEY=...  # base64 32-byte key
ALLOW_PLAINTEXT_TOKENS=false
TOKEN_ENCRYPTION_KEY_EXAMPLE=zEk_wde018v03bppMyBkRb6ZZ7qKwUfakNqtcIzDcJw=
```

OAuth endpoints:
- `GET /integrations/twitch/oauth/start`
- `POST /integrations/twitch/oauth/callback`
- `GET /integrations/youtube/oauth/start`
- `POST /integrations/youtube/oauth/callback`

## OAuth Refresh
```
POST /integrations/refresh
{ "platform": "twitch" }
```

## Twitch EventSub Webhook (Phase 3.2)
```
POST /integrations/webhooks/twitch
```

## Phase 3.5 (Full Phase 3 Completion)
- Automatic ingestion loop:
  - YouTube LiveChat polling every 15s
  - Twitch EventSub auto-subscribe (if metadata present)
- Live events feed:
  - `GET /api/events/stream` (SSE)

## Local Agent (Phase 4)
Env vars:
```
USE_LOCAL_AGENT=true
AGENT_ACCESS_KEY=change-me
AGENT_SIGNING_KEY=change-me-too
STREAMER_ID=1
KAZUMI_API_BASE=http://localhost:8000
AGENT_POLL_INTERVAL=0.5
AGENT_WS=true
```

## Smoke Test (Streamer + Viewer)
Run this after backend startup to validate core auth + dashboard + viewer flow end-to-end:
```bash
python scripts/smoke_e2e.py --base-url http://127.0.0.1:8000
```

## Production Hardening
Set these before go-live:
```
APP_ENV=production
FRONTEND_ORIGINS=https://app.your-domain.com
SENTRY_DSN=... # optional but recommended for backend error tracking
SENTRY_TRACES_SAMPLE_RATE=0.05
```

Notes:
- In production mode, if `FRONTEND_ORIGINS` is empty, backend CORS blocks all origins by default.
- CI now includes gitleaks secret scanning with `.gitleaks.toml` configuration.
OBS_HOST=localhost
OBS_PORT=4455
OBS_PASSWORD=your_obs_password
OBS_MIC_SOURCE=Mic/Aux
```

Run the stub agent:
```
python scripts/local_agent.py
```

Notes:
- The agent verifies signatures before acknowledging commands.
- OBS execution is currently a safe no-op in the stub.

## Moment Finder (Phase 6)
Set one search provider:
```
SEARCH_PROVIDER=serper   # or serpapi
SERPER_API_KEY=...
SERPAPI_KEY=...
```

If no key is set, the Moment Finder will return no results.

Saved Collections:
- Stored in localStorage key `kazumi_saved_moments`
- Clear localStorage to reset

## Acceptance Criteria

Kazumi can:
- ✅ Start without errors via `backend/main.py`
- ✅ Receive chat/dashboard commands
- ✅ Route through single brain for decisions
- ✅ Trigger observable actions (log, OBS call, WS event)

## Testing

Backend:
```
py -3.11 -m pytest -q
```

Frontend typecheck:
```
cd frontend/web
npm run typecheck
```

Notes:
- If tests fail due to missing env vars, populate `.env` first.
- OAuth flows require valid client IDs/secrets in `.env`.

Auto-clip MVP:
```
AUTO_CLIP_ENABLED=true
AUTO_CLIP_WINDOW_SEC=20
AUTO_CLIP_MIN_MESSAGES=12
AUTO_CLIP_COOLDOWN_SEC=90
```

Confidence gating:
```
CONFIDENCE_THRESHOLD=0.7
CONFIDENCE_THRESHOLD_SENSITIVE=0.9
```

Test flow:
1. Start OBS replay buffer (auto when AUTO_CLIP_ENABLED=true).
2. Ingest chat events quickly via `/api/ingest` (>= AUTO_CLIP_MIN_MESSAGES within window).
3. Confirm a new pending clip appears in the Clips dashboard.

Short-form export MVP:
1. Approve a clip so it appears in Recent Clips.
2. Click TikTok / Shorts / Reels buttons in Clip Management.
3. Confirm an export file appears in `backend/data/exports`.

ffmpeg:
- Install ffmpeg locally and ensure `ffmpeg` is in PATH.

## Auth Bypass (Dev Only)
To bypass the sign-in flow during local UI testing:
```
NEXT_PUBLIC_AUTH_BYPASS=true
```

Restart the frontend after setting it.

Or toggle it from Settings > Dev Tools (localStorage).

To undo:
- Set `NEXT_PUBLIC_AUTH_BYPASS=false` (or remove it).
- Clear localStorage key `kazumi_auth_bypass`.

## Development

- No new features without explicit approval
- One entrypoint, one brain, one OBS controller
- Aggressively delete unused code
- Prefer clarity over cleverness

What’s in place

New service: scoring.py
Sliding window (15s) hype meter
Weighted scoring (velocity + keywords + intensity)
Confidence bands: high / medium / low
Ingestion hook: events.py
Every chat message updates the scorer
Returns moment_score in the ingest response
Broadcasts moment_score to /ws/events when confidence is medium/high
How to verify quickly (PowerShell)

# send chat messages into ingest
$body = @{
  platform = "twitch"
  event_type = "chat"
  message = "OMG CLIP IT THIS IS INSANE"
  payload = @{ intensity = 70 }
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/ingest" -Body $body -ContentType "application/json"
You’ll get a response with moment_score and, if confidence ≥ medium, it will broadcast a moment_score event on the websocket.
How to verify (quick)
Restart backend:

uvicorn backend.main:app --reload
Then simulate hype messages:

$body = @{
  platform = "twitch"
  event_type = "chat"
  message = "OMG CLIP IT THIS IS INSANE POG"
  payload = @{ intensity = 80 }
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/ingest" -Body $body -ContentType "application/json"
Expected:

Response includes moment_score
If confidence is high, a clip is created (pending) and a CLIP_SAVED event is broadcast.
If confidence is medium, a suggestion appears in the command queue.
