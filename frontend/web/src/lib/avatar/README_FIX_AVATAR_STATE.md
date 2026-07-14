Fix for runtime error: `setAvatarState is not a function`.

Root cause:
- KazumiSidePanel.tsx expects `useAvatar()` to return `{ avatarState, setAvatarState }`.
- But current `useAvatar.js` only returns `{ avatarUrl, setAvatarUrl }`.

Intended behavior:
- Avatar components under `src/components/avatar/*` implement a state machine with states: idle, listening, thinking, speaking, alert.

Planned code change:
1) Update `frontend/web/src/lib/avatar/AvatarContext.jsx` to include:
   - `avatarState` (default: 'idle')
   - `setAvatarState`
2) Update `frontend/web/src/lib/avatar/useAvatar.js` to return:
   - `{ avatarState, setAvatarState, avatarUrl, setAvatarUrl }` (or at least the state parts used by KazumiSidePanel).

After this change:
- `KazumiSidePanel` will stop crashing.

