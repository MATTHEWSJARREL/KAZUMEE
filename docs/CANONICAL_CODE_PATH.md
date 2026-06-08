# Canonical Code Path (Kazumi)

This document defines the single source-of-truth module layout we should follow going forward.

## Backend Canonical Paths

- App entrypoint: `backend/main.py`
- HTTP API routes: `backend/api/routes/`
- WebSocket manager: `backend/api/websockets.py`
- AI decision/intent logic: `backend/brain/`
- Core runtime/services (auth, policy, observer, ingestion, pricing, voice): `backend/core/`
- OBS command/control execution: `backend/commands/`
- Database models/session: `backend/database/`
- Alembic migrations: `backend/alembic/versions/`
- Research/search modules: `backend/researcher/`
- Streamer orchestration helpers: `backend/director/`

## Frontend Canonical Paths

- App routes/layout: `frontend/web/src/app/`
- Shared UI components: `frontend/web/src/components/`
- Shared hooks: `frontend/web/src/hooks/`
- API/settings clients and context: `frontend/web/src/lib/`
- SSR/entry points: `frontend/web/src/entry.server.tsx`, `frontend/web/src/entry.client.tsx`

## Canonical Conventions

- Prefer TypeScript files for new frontend shared modules (`.ts`/`.tsx`) when equivalent `.jsx` files exist.
- Keep runtime/generated artifacts out of Git (`__pycache__/`, `*.pyc`, test reports, temp logs).
- Keep one migration system only (`backend/alembic`).

## Known Items To Resolve In Cleanup Pass

- WebSocket manager duplication:
  - `backend/api/websockets.py`
  - `backend/core/ws.py`
  Decide and converge on one manager implementation.

- Duplicate chat component implementation:
  - `frontend/web/src/components/KazumiChat.tsx`
  - `frontend/web/src/components/KazumiChat.jsx`
  Keep one canonical component and remove the duplicate.

- Accidental path/file candidate:
  - `frontend/web/src/hooks/{`
  Remove during delete pass.
