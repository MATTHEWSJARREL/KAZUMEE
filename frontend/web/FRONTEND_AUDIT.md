# Frontend Audit

Generated after cleanup. Scope: `frontend/web` only.

## Routing Rules

The app uses React Router with `src/app/routes.ts`. That file only registers files named `page.jsx`.

Active page routes:

| Route | File | Status |
| --- | --- | --- |
| `/` | `src/app/page.jsx` | ACTIVE streamer dashboard |
| `/analytics` | `src/app/analytics/page.jsx` | ACTIVE |
| `/auth` | `src/app/auth/page.jsx` | ACTIVE |
| `/clips` | `src/app/clips/page.jsx` | ACTIVE |
| `/commands` | `src/app/commands/page.jsx` | ACTIVE |
| `/ml-training` | `src/app/ml-training/page.jsx` | ACTIVE |
| `/moderation` | `src/app/moderation/page.jsx` | ACTIVE |
| `/pricing` | `src/app/pricing/page.jsx` | ACTIVE |
| `/settings` | `src/app/settings/page.jsx` | ACTIVE |
| `/setup` | `src/app/setup/page.jsx` | ACTIVE |
| `/stream-health` | `src/app/stream-health/page.jsx` | ACTIVE |
| `/viewer` | `src/app/viewer/page.jsx` | ACTIVE viewer page |
| `/voice` | `src/app/voice/page.jsx` | ACTIVE |
| `*?` | `src/app/__create/not-found.tsx` | ACTIVE fallback |

Legacy page-shaped files:

| Intended Route | File | Status | Reason |
| --- | --- | --- | --- |
| `/viewer/:streamerId` | `src/app/viewer/[streamerId]/page.tsx` | LEGACY | It is `page.tsx`, but the route generator only registers `page.jsx`. It is a complete older viewer implementation, so it was not deleted as unused. |

Production local API route files are loaded from `src/app/api/**/route.js` by `__create/route-builder.ts`. In dev, `vite.config.ts` proxies `/api` to `http://127.0.0.1:8000`, so backend API behavior can differ between dev and production.

## Reachable User Pages

Reachable through auth redirects, nav links, or route tests:

- `/` streamer dashboard: `src/app/page.jsx`
- `/viewer`: `src/app/viewer/page.jsx`
- `/auth`: `src/app/auth/page.jsx`
- `/settings`: `src/app/settings/page.jsx`
- `/clips`: `src/app/clips/page.jsx`
- `/commands`: `src/app/commands/page.jsx`
- `/moderation`: `src/app/moderation/page.jsx`
- `/analytics`: `src/app/analytics/page.jsx`
- `/ml-training`: `src/app/ml-training/page.jsx`
- `/stream-health`: `src/app/stream-health/page.jsx`
- `/voice`: `src/app/voice/page.jsx`
- `/pricing`: `src/app/pricing/page.jsx`
- `/setup`: `src/app/setup/page.jsx`

## Component Tree

```text
root.tsx
  Layout
    QueryClientProvider
      SettingsProvider
        ClipSearchProvider
          RoleGuard
          Outlet
            / -> KazumiDashboard
              ObsStatus
              AIApprovalDashboard
              ClipManagement
            /viewer -> ViewerModePage
              CatchUpClipCard (local component)
            /voice -> VoicePage
              ObsStatus
            /pricing -> PricingPage
              PricingSection
            other page.jsx routes render page-local UI only
          GlobalExperience
            ClipSearchResults
            KazumiChat
      KazumiSidePanel
```

Legacy-only component tree:

```text
viewer/[streamerId]/page.tsx (not routed today)
  ViewerTopBar
  VibeBar
  ClipCard
  CatchUpNudge
```

## Imported Components

ACTIVE:

- `AIApprovalDashboard.jsx`: rendered by `/`
- `ClipManagement.jsx`: rendered by `/`
- `ClipSearchResults.jsx`: rendered globally in `root.tsx`
- `KazumiChat.tsx`: rendered globally in `root.tsx`
- `KazumiSidePanel.tsx`: rendered globally in `root.tsx`
- `ObsStatus.jsx`: rendered by `root.tsx`, `/`, and `/voice`
- `PricingSection.jsx`: rendered by `/pricing`

LEGACY:

- `CatchUpNudge.tsx`: only imported by legacy `viewer/[streamerId]/page.tsx`
- `ClipCard.tsx`: only imported by legacy `viewer/[streamerId]/page.tsx`
- `VibeBar.tsx`: only imported by legacy `viewer/[streamerId]/page.tsx`
- `ViewerTopBar.tsx`: only imported by legacy `viewer/[streamerId]/page.tsx`

UNUSED and removed:

- `src/components/AmbientBackground.tsx`: no imports, no route, no dynamic loading
- `src/components/ConfirmationOverlay.tsx`: no imports, no route, no dynamic loading
- `src/components/GlassCard.tsx`: no imports, no route, no dynamic loading
- `src/components/UpgradeModal.tsx`: no imports, no route, no dynamic loading
- `src/components/VoiceSafetySettings.tsx`: no imports, no route, no dynamic loading

## Active CSS Imports

ACTIVE:

- `src/app/global.css`: imported by `src/app/root.tsx`
- `src/app/viewer/viewer.redesign.css`: imported by active `/viewer`

LEGACY:

- `src/app/viewer/[streamerId]/viewer.module.css`: imported by legacy `viewer/[streamerId]/page.tsx`
- `src/components/CatchUpNudge.module.css`: legacy-only
- `src/components/ClipCard.module.css`: legacy-only
- `src/components/VibeBar.module.css`: legacy-only
- `src/components/ViewerTopBar.module.css`: legacy-only

UNUSED and removed:

- `src/index.css`: not imported anywhere
- `src/components/AmbientBackground.module.css`: only used by removed component
- `src/components/ConfirmationOverlay.module.css`: only used by removed component
- `src/components/GlassCard.module.css`: only used by removed component
- `src/components/UpgradeModal.module.css`: only used by removed component
- `src/components/VoiceSafetySettings.module.css`: only used by removed component

## API Endpoints Called By Frontend

Auth:

- `/auth/me`
- `/auth/login`
- `/auth/register`
- `/auth/role`
- `/auth/active-streamer`
- `/auth/stream-token`
- `/auth/streamers`
- `/auth/password-reset/request`
- `/auth/verify/request`

Streamer dashboard and events:

- `/api/dashboard`
- `/api/events/stream`
- `/api/events/streamer-view?window_minutes=15&limit=300`
- `/api/events/streamer-view/answer`
- `/api/events/recent?limit=40`
- `/api/streamer/director/post-stream-report?hours=6`
- `/api/streamer/ai/status`
- `/api/moment-finder/search`
- `/api/commands/process`

Viewer:

- `/api/viewer/dashboard`
- `/api/viewer/credits`
- `/api/viewer/preferences`
- `/api/viewer/chat-cleanse/preferences`
- `/api/viewer/companion/analyze`
- `/api/viewer/companion/sent`
- `/api/viewer/companion/status?tracking_id=...`
- `/api/viewer/companion/mark-answered`
- `/api/viewer/companion/retry-suggestion`
- `/api/viewer/catchup/highlights`
- `/api/viewer/catchup/recap?mode=...`
- `/api/viewer/vibe-matcher/recommendations?mood=...&limit=5`
- `/api/viewer/clip/request`
- `/api/viewer/vote`
- `/api/viewer/redeem`

OBS and setup:

- `/obs/status`
- `/obs/sources`
- `/obs/cameras`
- `/obs/sources/visibility`
- `/obs/sources/device`
- `/integrations/status`
- `/integrations/metadata`
- `/integrations/metadata?platform=...`
- `/integrations/diagnostics`
- `/integrations/connect`
- `/integrations/twitch/subscribe`
- `/integrations/youtube/livechat/poll`
- `/policy`

Feature pages:

- `/api/analytics?range=...`
- `/api/health`
- `/api/stream-health`
- `/api/clips?filter=...`
- `/api/commands?status=...&tier=...`
- `/api/commands/:id/execute`
- `/api/commands/:id/reject`
- `/api/ml-training`
- `/api/ml-training/feedback`
- `/api/preferences`
- `/api/preferences/presets`
- `/api/preferences/preset`
- `/api/voice-agent/status`
- `/api/voice-agent/logs?limit=15`
- `/api/voice-agent/start`
- `/api/voice-agent/stop`
- `/api/voice-agent/irl/status`
- `/api/voice-agent/irl/start`
- `/api/voice-agent/irl/stop`
- `/moderation/queue?limit=60`
- `/moderation/cases?status=resolved&limit=20`
- `/moderation/metrics?hours=24`
- `/moderation/audit?limit=40`
- `/moderation/cases/:caseId/review`
- `/moderation/bundles/apply`
- `/moderation/panic`
- `/clips/pending`
- `/clips/recent?limit=20`
- `/clips/review`
- `/clips/open`
- `/clips/:clipId/export`
- `/commands/:id/status`

Legacy-only endpoints:

- `/api/streamer/:streamerId`
- `/api/streamer/:streamerId/vibe`
- `/api/clips?streamer_id=:streamerId&limit=20`

## Referenced Assets

ACTIVE:

- `/logo.png` -> `public/logo.png`, used by active `/viewer`. Note: current file is 0 bytes and should be replaced with a valid image.
- Google Fonts stylesheet in `root.tsx`.

Dynamic/user-data assets:

- `clip.thumbnail_url`, `clip.url`
- `streamer.avatar_url`, `streamer.profile_image_url`, `streamer.url`
- external Twitch/YouTube URLs opened by viewer search

Internal/tooling:

- `src/__create/favicon.png`
- Create loading GIF used by `src/__create/HotReload.tsx`
- Tailwind CDN in `__create/get-html-for-error-page.ts`

## NPM Packages

Used by runtime/app/config/tests:

- `@babel/core`
- `@babel/preset-react`
- `@babel/preset-typescript`
- `@babel/types`
- `@neondatabase/serverless`
- `@playwright/test`
- `@react-router/dev`
- `@react-router/node`
- `@testing-library/jest-dom`
- `@tanstack/react-query`
- `fast-glob`
- `lodash-es` through the `lodash` alias
- `lucide-react`
- `micromatch`
- `postcss`
- `react`
- `react-dom`
- `react-idle-timer`
- `react-router`
- `react-router-dom`
- `react-router-hono-server`
- `serialize-error`
- `sonner`
- `stripe`
- `styled-jsx`
- `tailwindcss`
- `typescript`
- `vite`
- `vite-plugin-babel`
- `vite-tsconfig-paths`
- `vitest`
- `zustand`

No direct imports found in frontend source/config after cleanup:

- `@babel/generator`
- `@babel/plugin-transform-react-jsx`
- `@babel/traverse`
- `@chakra-ui/react`
- `@dnd-kit/core`
- `@dnd-kit/sortable`
- `@emotion/react`
- `@emotion/styled`
- `@lshay/ui`
- `@react-aria/button`
- `@react-router/fs-routes`
- `@tanstack/react-table`
- `@testing-library/react`
- `@vis.gl/react-google-maps`
- `argon2`
- `classnames`
- `clean-stack`
- `cmdk`
- `color2k`
- `date-fns`
- `downshift`
- `html-to-image`
- `isbot`
- `jsdom`
- `lodash`
- `motion`
- `papaparse`
- `pdfjs-dist`
- `react-colorful`
- `react-day-picker`
- `react-hook-form`
- `react-markdown`
- `react-resizable-panels`
- `recharts`
- `remark-gfm`
- `tailwind-merge`
- `three`
- `vaul`
- `ws`
- `yup`

These package entries were not removed in this pass because the request asked to delete files confirmed unused, not to rewrite dependency manifests.

## Removed Files

| File | Why unused | Depends on it |
| --- | --- | --- |
| `src/index.css` | No imports; app imports `src/app/global.css` instead | Nothing |
| `src/app/api/vitest.config.ts` | Nested config not referenced by root Vitest config or scripts | Nothing |
| `src/components/AmbientBackground.tsx` | No imports, no routes, no dynamic loading | Nothing |
| `src/components/AmbientBackground.module.css` | Only imported by removed component | Removed component |
| `src/components/ConfirmationOverlay.tsx` | No imports, no routes, no dynamic loading | Nothing |
| `src/components/ConfirmationOverlay.module.css` | Only imported by removed component | Removed component |
| `src/components/GlassCard.tsx` | No imports, no routes, no dynamic loading | Nothing |
| `src/components/GlassCard.module.css` | Only imported by removed component | Removed component |
| `src/components/UpgradeModal.tsx` | No imports, no routes, no dynamic loading | Nothing |
| `src/components/UpgradeModal.module.css` | Only imported by removed component | Removed component |
| `src/components/VoiceSafetySettings.tsx` | No imports, no routes, no dynamic loading | Nothing |
| `src/components/VoiceSafetySettings.module.css` | Only imported by removed component | Removed component |
| `src/hooks/usePulseAnimation.js` | No external imports | Nothing |
| `src/lib/obsClient.js` | No external imports | Nothing |
| `src/lib/commandClient.js` | No external imports | Nothing |
| `src/utils/useAuth.js` | No external imports | Nothing |
| `src/utils/useHandleStreamResponse.js` | No external imports | Nothing |
| `src/utils/useUpload.js` | No external imports | Nothing |
| `src/utils/useUser.js` | No external imports | Nothing |

## Architecture Diagram

```text
Browser
  |
  v
React Router app
  |
  +-- root.tsx document shell
  |     +-- global.css
  |     +-- QueryClientProvider
  |     +-- SettingsProvider
  |     +-- ClipSearchProvider
  |     +-- RoleGuard
  |     +-- GlobalExperience
  |     |     +-- ClipSearchResults
  |     |     +-- KazumiChat
  |     +-- KazumiSidePanel
  |
  +-- page routes generated from src/app/**/page.jsx
        +-- / -> streamer dashboard
        +-- /viewer -> viewer experience
        +-- /settings, /voice, /clips, /commands, /analytics, ...

API access
  |
  +-- apiFetch/buildApiUrl -> FastAPI backend base URL
  +-- EventSource -> /api/events/stream
  +-- dev proxy -> /api to backend
  +-- production local Hono route loader -> src/app/api/**/route.js
```

## Removal Plan

Completed:

1. Removed files with no imports, no routing, no dynamic import evidence, and no build/config references.
2. Left legacy `viewer/[streamerId]` files in place because they are an old implementation, not a random orphan.
3. Restored active `viewer.redesign.css` because active `/viewer` imports it.

Recommended next cleanup, not performed automatically:

1. Decide whether `/viewer/[streamerId]` should be revived by route generation or removed as legacy.
2. Decide whether `src/app/api/**` local routes are production-critical or should be replaced entirely by backend calls.
3. Replace `public/logo.png`, which is currently an empty file.
4. Review unused package entries separately and prune with a dependency-focused PR.
