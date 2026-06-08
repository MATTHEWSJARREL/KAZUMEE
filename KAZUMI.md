# KAZUMI - Technical Handoff

Last updated: 2026-04-16 (Africa/Nairobi)

## 1) What Kazumi Is

Kazumi is a multi-tenant AI streaming copilot with two primary product surfaces:

1. Streamer mode:
- OBS control and stream operations
- AI director features (polling, search, tactical backseat, safety actions, post-stream reporting)
- Moderation workflows and anti-abuse controls
- Clip lifecycle and short-form export pipeline
- Voice-agent controls

2. Viewer mode:
- Personalized companion layer for stream interaction
- Vibe matching, catch-up recap/highlights, clip requests
- Chat cleanse and latency shielding
- Viewer voting, credits, and policy-gated requests

The backend is a FastAPI monolith with modular routers and shared core services. The frontend is a React Router (Vite) app.

## 2) What Has Been Achieved

### Core Platform
- Multi-tenant auth model with streamer/viewer roles and streamer scoping.
- Session/token flows with role-aware behavior (`/auth/me`, `/auth/stream-token`).
- Runtime schema compatibility patching in `backend/main.py`.
- Centralized event ingestion and SSE streaming for live client updates.

### Streamer Side
- Director API suite in `backend/api/routes/director.py`:
- Dynamic poll generation
- Universal search
- Game backseat advice
- Safety trigger and vision scan hooks
- Audio level controls
- Clip-now + editor packaging flows
- Shield and moderation enforce actions
- Post-stream reports

- Streamer AI suite in `backend/core/streamer_ai_suite.py`:
- Dynamic prompter
- Sentiment shield / nuance handling
- Anti-raid heuristics
- Stream doctor heuristics
- Spoiler filter logic
- Empathy guard heuristics
- Audio safe mode hooks
- TOS bodyguard rule logic
- Audience-agent support methods

### Viewer Side
- Viewer dashboard, credits, preferences, and chat-cleanse preferences.
- Vibe matcher recommendations endpoint.
- Catch-up recap + highlight generation endpoints.
- Viewer clip request path and vote/redeem/sound actions.
- Streamer discovery/search in viewer flow with local + external results:
- Ranked candidates
- External diagnostics payload
- Direct external URLs

### Moderation
- Moderation queue/cases/audit/metrics endpoints.
- Action bundle endpoint and panic endpoint.
- Case review workflow.

### Integrations
- OAuth connect flows for Twitch/YouTube in `backend/api/routes/integrations.py`.
- Encrypted token storage via `backend/core/crypto.py`.
- Metadata save/read, diagnostics endpoint with live connectivity checks.
- Twitch webhook and YouTube live chat poll ingestion paths.

### Commands + Agent
- Command processing/execute/review APIs.
- Local agent interface (`/agent/commands/next`, `/agent/commands/{id}/ack`).
- Signed command model (`AGENT_ACCESS_KEY`, `AGENT_SIGNING_KEY`).
- Local agent runtime in `scripts/local_agent.py` with OBS and ffmpeg export support.

### ML / Learning
- Taste-profile learning and clip feedback loop.
- Versioned ML artifact model: `backend/database/models/ml_model_artifact.py`.
- `/api/ml-training` now returns artifact + history metadata and non-simulated status.
- Training endpoint creates new evaluated model artifacts with version increments.

### Voice
- Voice agent service in `backend/core/voice_agent.py`.
- Start/stop/status/log APIs at `/api/voice-agent/*`.
- Wake-word parsing and command dispatch to backend command callback.

### Ops / Quality
- Health endpoints (`/health`, `/api/health`, stream health endpoints).
- Optional Sentry wiring in backend.
- Secret scanning config (`.gitleaks.toml`) and CI wiring.
- Smoke test script for streamer+viewer happy path: `scripts/smoke_e2e.py`.

## 3) Known Gaps / Work Left

1. Advanced AI realism gaps:
- Some "AI" areas are still heuristic-first, not deep model pipelines.
- `create_clip` command path in `backend/commands/executor.py` still has placeholder behavior.

2. Full production readiness gaps:
- Background loops still run in-process with API app; ideal split is API workers + dedicated worker services.
- Full alerting/on-call policy is not fully codified (Sentry optional, but operational runbooks should be expanded).

3. Streamer growth/monetization gaps:
- Pricing endpoint is config-driven (`backend/config/pricing.json`) and not a full billing system.
- Lemon Squeezy/Stripe checkout + webhook subscription enforcement is not fully integrated in backend auth/entitlements yet.

4. ML maturity gaps:
- Artifact persistence exists, but model lifecycle is still profile/heuristic-centric.
- No independent training jobs, feature store, or model registry service beyond DB artifact rows.

5. UX/codebase cleanup gaps:
- `docs/CANONICAL_CODE_PATH.md` still lists cleanup items (duplicate websocket manager path ambiguity, duplicate component cleanup, `__create` residue).

6. Always-on "Jarvis" maturity:
- Voice agent is functional, but true always-on multimodal orchestration still needs stronger safety, privacy gating, and wake-word pipeline hardening for production.

## 4) Tech Stack Used

### Backend
- FastAPI, Uvicorn, Gunicorn
- SQLAlchemy + Alembic
- PostgreSQL (primary expected target)
- obsws-python for OBS WebSocket control
- Groq SDK for LLM calls
- ChromaDB + sentence-transformers for clip search/vector use cases
- WebSockets + SSE for realtime feeds
- SpeechRecognition + PyAudio for voice input
- Optional sentry-sdk for error tracking

Primary dependency file: `requirements.txt`

### Frontend
- React 18 + React Router 7 + Vite
- TypeScript tooling and Playwright for e2e
- UI libs include Chakra, Lucide, TanStack, Recharts

Primary dependency file: `frontend/web/package.json`

### Storage / Data
- Relational schema in `backend/database/models/`
- Optional local vector data under `backend/data/vector_db/`
- Runtime JSON fields for policy/settings/profiles/metrics

## 5) System Architecture

### Request/Action Pipeline (typical)

1. Client sends action/command request.
2. Backend resolves auth + streamer context (`resolve_streamer_id`).
3. Policy evaluates action risk and tier eligibility.
4. Command is queued/executed depending on action type and permissions.
5. OBS execution happens via adapter/executor (direct) or local agent (signed command path).
6. Events are emitted to SSE/WebSocket feeds and persisted for analytics/reporting.

### Ingestion Pipeline

1. Ingested events enter `/api/ingest`.
2. Event normalization + dedupe + storage.
3. Side-effects feed viewer/streamer UI streams and downstream AI logic.
4. Auto-clip and scoring hooks run off the observed event stream.

### Voice Pipeline

1. Voice agent starts from `/api/voice-agent/start`.
2. Microphone listener transcribes speech.
3. Wake-word extractor gates command.
4. Command callback dispatches into backend command execution.
5. Logs exposed via `/api/voice-agent/logs`.

## 6) FastAPI Surface (Operational Map)

Main app entry: `backend/main.py`

Core app endpoints:
- `GET /`
- `GET /api/auth/session`
- `GET /api/auth/csrf`
- `GET /health`
- `GET /api/health`
- `GET /api/analytics`
- `GET /api/stream-health`
- `GET /api/commands`
- `POST /api/commands/{command_id}/execute`
- `POST /api/commands/{command_id}/reject`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /command`
- `POST /api/commands/process`
- `POST /api/commands/clear`
- `GET /events/log`
- `GET /api/viewer/dashboard`
- `GET /api/dashboard`
- `POST /api/mode/toggle`
- `POST /system/restart`

Mounted routers:
- `analytics.router` at `/analytics`
- `auth.router` at `/auth`
- `clips.router` at `/api/clips` and `/clips`
- `commands.router` at `/commands`
- `moderation.router` at `/moderation`
- `streams.router` at `/streams`
- `events.router` (no extra prefix)
- `integrations.router` at `/integrations`
- `policy.router` at `/policy`
- `agent.router` at `/agent`
- `moment_finder.router` at `/api/moment-finder`
- `preferences.router` (no extra prefix)
- `viewer_actions.router` (no extra prefix)
- `settings.router` (no extra prefix)
- `assistant.router` (no extra prefix)
- `pricing.router` (no extra prefix)
- `streamer_ai.router` (no extra prefix)
- `director.router` (no extra prefix)
- `ml_training.router` (no extra prefix)
- `voice_agent.router` at `/api/voice-agent`
- `obs.router` at `/obs`

To regenerate the endpoint inventory quickly:

```powershell
rg -n "@router\.(get|post|put|patch|delete)\(" backend/api/routes --glob "*.py"
rg -n "include_router\(|@app\.(get|post|put|patch|delete)\(" backend/main.py
```

## 7) Data Model Overview

Core DB models in `backend/database/models/`:

- Identity/session:
- `user.py`, `user_session.py`

- Tenancy/actors:
- `streamer.py`, `viewer.py`, `community.py`

- Stream runtime:
- `stream_session.py`, `stream_event.py`

- Commands and execution:
- `command.py`, `command_result.py`, `command_log.py`, `agent_command.py`

- Content artifacts:
- `clip.py`, `assistant_message.py`, `viewer_action.py`

- Integrations:
- `platform_connection.py`

- ML artifacting:
- `ml_model_artifact.py`

Key multi-tenant fields:
- `streamer_id` on command/event/clip/action rows.
- Viewer active streamer linkage through `viewer.active_streamer_id`.

## 8) Security and Access Model

1. Role-based access:
- Streamer-only endpoints enforce role + streamer context.
- Viewer endpoints scoped to active streamer and policy.

2. Token handling:
- Session tokens for auth.
- Stream access token for SSE/event stream (`/auth/stream-token`).
- Integration tokens are encrypted at rest (token encryption key required in production).

3. Agent trust boundary:
- Agent key auth + command signature validation.
- Agent executes only when signature verifies.

4. Production hardening:
- Strict CORS config via `FRONTEND_ORIGINS`.
- Optional Sentry.
- Secret scanning config present.

## 9) What You Need To Buy / Provision

Minimum launch purchases:

1. Domain:
- Buy from Cloudflare Registrar (or equivalent).
- Use for app + API subdomains.

2. Compute host:
- Railway Hobby or a Linux VPS.
- Run backend + frontend deploy targets.

3. Postgres:
- Managed Postgres (Neon/Supabase/RDS) recommended for reliability.

4. Optional but strongly recommended:
- Error tracking (Sentry)
- Object storage for media exports (R2/S3-compatible)
- Transactional email provider for auth flows

API/platform accounts required (mostly free to create):
- Twitch developer app (`TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`)
- YouTube/Google app (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_API_KEY`)
- Groq API key (`GROQ_API_KEY`)
- OBS WebSocket enabled on streamer machine (`OBS_HOST`, `OBS_PORT`, `OBS_PASSWORD`)

## 10) Environment Configuration Matrix

Common required vars:
- `DATABASE_URL`
- `NEXT_PUBLIC_API_URL` (frontend)
- `NEXT_PUBLIC_WS_URL` (frontend)

Auth/session/security:
- `SESSION_DAYS`
- `SESSION_TOKEN_PEPPER`
- `STREAM_TOKEN_SECRET`
- `REQUIRE_AUTH`

CORS and runtime:
- `APP_ENV`
- `FRONTEND_ORIGINS`
- `PUBLIC_BASE_URL`
- `FRONTEND_BASE_URL`

Integrations:
- `TWITCH_CLIENT_ID`
- `TWITCH_CLIENT_SECRET`
- `TWITCH_WEBHOOK_SECRET`
- `TWITCH_WEBHOOK_URL`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_API_KEY`
- `TOKEN_ENCRYPTION_KEY`
- `ALLOW_PLAINTEXT_TOKENS`

AI/search:
- `GROQ_API_KEY`
- `SERPER_API_KEY` or `SERPAPI_KEY`
- `SEARCH_PROVIDER`

Agent and signing:
- `USE_LOCAL_AGENT`
- `AGENT_ACCESS_KEY`
- `AGENT_SIGNING_KEY`
- `STREAMER_ID`
- `KAZUMI_API_BASE`
- `AGENT_POLL_INTERVAL`
- `AGENT_WS`

Auto clip/stream doctor/policy tuning:
- `AUTO_CLIP_ENABLED`
- `AUTO_CLIP_WINDOW_SEC`
- `AUTO_CLIP_MIN_MESSAGES`
- `AUTO_CLIP_COOLDOWN_SEC`
- `STREAM_DOCTOR_AUTO_APPLY`
- `CONFIDENCE_THRESHOLD`
- `CONFIDENCE_THRESHOLD_SENSITIVE`
- `VOTE_WINDOW_SEC`
- `VOTE_THRESHOLD`

Observability:
- `SENTRY_DSN`
- `SENTRY_TRACES_SAMPLE_RATE`

## 11) Test and Validation

Backend tests:

```powershell
py -3.11 -m pytest -q
```

Frontend typecheck:

```powershell
cd frontend/web
npm run typecheck
```

Smoke e2e (backend running):

```powershell
python scripts/smoke_e2e.py --base-url http://127.0.0.1:8000
```

## 12) Recommended Next Work Order

1. Deploy baseline stack (domain + host + Postgres + env + CORS + health checks).
2. Complete billing/entitlements integration with webhook-driven plan enforcement.
3. Split background loops into dedicated worker process(es) before scaling API workers.
4. Replace remaining heuristic placeholders (clip create and advanced safety/DMCA detection paths).
5. Expand automated test coverage for streamer/viewer critical flows and auth edge cases.
6. Complete canonical cleanup pass from `docs/CANONICAL_CODE_PATH.md`.

