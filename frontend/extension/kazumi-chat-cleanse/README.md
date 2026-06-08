# Kazumi Viewer Companion Extension

Browser extension for viewer-side chat comfort on Twitch and YouTube.

## What It Does

- Applies personal chat filtering directly in platform chat DOM.
- Applies client-side audio leveling to stream playback:
  - voice boost
  - game tame (low-frequency reduction)
  - smart leveling compressor
  - master gain control
- Applies optional latency sync:
  - delays chat rendering locally so chat timing better matches delayed video playback
  - configurable delay (0-8s)
- Supports `Chill`, `Balanced`, `Strict`, and `Custom` modes.
- Keeps filtering transparent:
  - Shows hidden counts and reason breakdown.
  - Collapses messages instead of deleting.
  - Lets viewer reveal hidden messages at any time.
- Supports whitelist phrases/emotes.
- Supports optional cloud scoring (`localScoringOnly = false`) with local fallback.
- Syncs profile with Kazumi viewer account:
  - `GET /api/viewer/chat-cleanse/preferences`
  - `PUT /api/viewer/chat-cleanse/preferences`

## Load In Chrome

1. Open `chrome://extensions`.
2. Enable `Developer mode`.
3. Click `Load unpacked`.
4. Select this folder: `frontend/extension/kazumi-chat-cleanse`.

## Connect To Kazumi

1. Open the extension popup.
2. Set API URL (for local dev: `http://localhost:8000`).
3. Login with a viewer account.
4. Click `Pull Cloud` to import your account profile.
5. Tune settings and click `Push Cloud` to sync.

## Notes

- Filtering is personal-only. It does not moderate or punish chat users.
- Audio leveling is enhancement-based in browser (not full source-stem extraction yet).
- Default behavior is on-device scoring for privacy.
- If cloud scoring is enabled and API call fails, extension automatically falls back to local scoring.
