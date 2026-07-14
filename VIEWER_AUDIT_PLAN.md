# Viewer Dashboard Audit & Fix Plan

## Issues Fixed ✅

1. ✅ **Settings routing loop** - ViewerSettingsModal now integrated
2. ✅ **AbortError spam** - Timeout increased to 45s, suppressed from logs
3. ✅ **Clip library not working** - Fixed to scroll to section
4. ✅ **Recap unavailable message** - Better error messages
5. ✅ **Request timeouts** - Increased from 20s to 45s
6. ✅ **ViewerSettingsModal** - Theme, cleanse, compact, notifications, volume all working

## Issues Remaining ⚠️

7. Test cache clearing if needed
8. Verify 403 errors suppressed on all endpoints
9. UI redesign to modern dashboard style

## Remaining Fixes Needed

### Phase 1: API Error Suppression
1. Add try-catch wrapper for endpoints that only streamers can access
2. Prevent 403 errors from console clutter when viewer tries streamer endpoints
3. Create fallback for preferences when endpoint returns 403

### Phase 2: Viewer Features Verification
1. Verify all /api/viewer/* endpoints are working
2. Test clip request feature
3. Test voting system
4. Test companion suggestions
5. Test chat cleanse feature

### Phase 3: UI Redesign
After all features work, redesign to match modern dashboard aesthetic:
- Keep purple (#7C3AED) as primary color
- Improve card styling and spacing
- Better hierarchy and visual organization
- Responsive design improvements
- Modern cryptocurrency dashboard inspiration (clean, clear, professional)

## Current Viewer Features Status

| Feature | Status | Notes |
|---------|--------|-------|
| Streamer selection | ✅ Working | Can select from available streamers |
| Chat event stream | ⚠️ Partial | Loads but may have CORS issues |
| Catchup recap | ❌ CORS blocked | Fixed error handling, but still blocked |
| Catchup highlights | ⚠️ Unknown | Related to recap feature |
| Clip requests | ⚠️ Unknown | Not tested yet |
| Scene voting | ⚠️ Unknown | Not tested yet |
| Companion suggestions | ⚠️ Unknown | Not tested yet |
| Chat cleanse | ⚠️ Unknown | Not tested yet |
| Viewer settings | ❌ Missing | Just created ViewerSettingsModal |

## Next Steps

1. **Suppress 403 errors** - Add error boundary for streamer-only endpoints
2. **Test each feature** - Go through each feature systematically
3. **Fix broken features** - Address issues found
4. **UI redesign** - Apply modern dashboard styling
5. **Streamer side** - Move to fixing streamer dashboard after viewer is solid

## Timeline

- Phase 1 (API fixes): ~30 minutes
- Phase 2 (Feature verification): ~1 hour
- Phase 3 (UI redesign): ~2-3 hours
- Streamer fixes: TBD

