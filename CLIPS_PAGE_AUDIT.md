# Clips Page & Storage Audit Report

**Date:** 2026-08-25  
**Status:** Report only — NO changes made

---

## 1. THUMBNAILS: Backend Generation

**Finding:** Column exists but unused (set to None)

- **Model:** `backend/database/models/clip.py:16`
  - `thumbnail_path = Column(String, nullable=True)` ✅ (exists)
- **Ingest Path:** `backend/api/routes/clips.py:974-985`
  - Creates new clip record
  - **Does NOT set thumbnail_path** (always None)
  - No thumbnail generation code in ingest pipeline
- **API Response:** Returns `"thumbnail_path": clip.thumbnail_path` (clips.py:165)
  - Will be `null` for all clips currently

**Status:** 🔴 **NOT IMPLEMENTED** — Column ready but never populated

---

## 2. FFMPEG AVAILABILITY

**Finding:** ✅ **Available and already used**

- **Transcode Function:** `backend/api/routes/clips.py:30-80`
  - Uses `ffmpeg` for MP4/H.264/AAC conversion
  - Used on every clip ingest (line 964)
  - Checks availability at runtime (line 50)
- **Codec Check Function:** `backend/api/routes/clips.py:83-122`
  - Uses `ffprobe` to analyze input codec
  - Called before transcode
  - Falls back gracefully if ffprobe unavailable
- **Dockerfile:** Line 5-7 installs ffmpeg
  - Both ffmpeg and ffprobe available in production

**Status:** ✅ **READY** — No new dependencies needed for thumbnail extraction

---

## 3. FRONTEND CLIP CARDS: Current Rendering

**File:** `frontend/web/src/app/clips/page.jsx`

**What renders per clip card:**
```
┌─────────────────────────────────┐
│ □ [Placeholder Icon]  (Published) │  ← Status overlay
│   ◀ PLAY BUTTON                   │
├─────────────────────────────────┤
│ Title                            │
│ Description                      │
│ Quality: 75%  │  [timestamp]     │  ← Only quality score shown
├─────────────────────────────────┤
│ [Approve] [Reject] [Delete]...   │  ← Action buttons
└─────────────────────────────────┘
```

**Missing/Incomplete:**
- ❌ **Actual thumbnail image** (line 447-450 shows placeholder Video icon)
- ❌ **Duration display** (not rendered, but API provides duration_seconds)
- ⚠️ **Timestamp clarity** (shows only date created, not relative time)
- ✅ **Status indicators** (published/processing badges exist)

**Empty & Loading States:**
- ✅ **Loading state** (line 429-430): "Loading clips..." message
- ✅ **Empty state** (line 431-436): Icon + message + description

**Status:** 🟡 **PARTIAL** — Cards have structure, need thumbnails + duration metadata

---

## 4. CLIP API RESPONSE: Fields Returned

**Endpoint:** `GET /api/clips/` (clips.py:142-187)

**Fields per clip:**
```json
{
  "id": 123,
  "title": "string",
  "description": "string",
  "file_path": "/path/to/clip.mp4",
  "thumbnail_path": null,           // Always null (not generated)
  "status": "pending|approved|rejected|deleted",
  "requested_by_type": "ai|viewer|streamer",
  "requested_by_name": "string",
  "created_at": "2026-08-25T...",   // ISO timestamp
  "approved_at": null,               // ISO timestamp if approved
  "quality_score": 0.75,             // 0-1 scale
  "tags": [...],
  "duration_seconds": 45.0,          // ✅ AVAILABLE but not rendered
  "export_status": "queued|sent|executed|error",
  "export_preset": "tiktok|shorts|reels",
  "export_path": null,
  "export_updated_at": null,
  "notes": "string",
  "urls": {
    "stream": "http://backend/api/clips/stream/123",
    "download": "http://backend/api/clips/download/123"
  }
}
```

**Summary:**
- ✅ All needed metadata present (duration, timestamps, quality)
- ❌ thumbnail_path always null
- ✅ URLs for stream/download included

**Status:** ✅ **GOOD** — Backend provides everything; frontend underutilizes

---

## 5. EMPTY & LOADING STATES

**File:** `frontend/web/src/app/clips/page.jsx`

**Loading State** (line 429-430):
```jsx
{loading ? (
  <div className={styles.loadingState}>Loading clips...</div>
) : ...}
```
- Simple text message
- No spinner/animation
- Minimal styling

**Empty State** (line 431-436):
```jsx
{filteredClips.length === 0 ? (
  <div className={styles.emptyState}>
    <Video size={48} />
    <p>No clips yet</p>
    <span>Clips will appear here as moments are detected</span>
  </div>
) : ...}
```
- ✅ Icon (Video from lucide)
- ✅ Headline
- ✅ Helpful description

**Status:** 🟡 **BASIC** — States exist but minimal animation/polish. Could add spinner to loading.

---

## 6. CLIP FILE STORAGE PATH

**File Path:** `backend/api/routes/clips.py:133`
```python
BASE_CLIPS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "clips"))
# Resolves to: backend/data/clips/
```

**How Stored:**
- On ingest (line 947-953):
  - Create `backend/data/clips/` directory
  - Generate UUID for each clip
  - Save as: `backend/data/clips/{uuid}.mp4`
  - Store full path in DB

**Railway Deployment:**
- ❌ **NO persistent volume configured**
- Files are stored on ephemeral container disk
- Will be wiped on redeploy/restart
- Current setup: ✅ Works for single session, ❌ Not suitable for production with user clips persisting

**Status:** 🔴 **EPHEMERAL** — Files deleted on redeploy (unless Railway Volume added)

---

## 7. DATABASE vs FILE PERSISTENCE

**Current State:**
- ✅ **Database:** Clip records persist across redeploys (PostgreSQL on Railway)
  - Clip metadata (title, status, timestamps) survives
- ❌ **Files:** MP4s are deleted on redeploy
  - `backend/data/clips/*.mp4` is ephemeral container storage
  - No S3 or persistent volume configured

**Result:**
```
POST /api/clips/ingest (agent uploads)
  ├─ MP4 saved to /backend/data/clips/{uuid}.mp4
  └─ DB record created pointing to that path
     
REDEPLOY happens
  ├─ Container destroyed
  ├─ /backend/data/clips/ wiped
  └─ DB record still exists but file_path is now dead link
  
GET /api/clips/stream/123
  └─ File not found (404) ← endpoint checks os.path.exists()
```

**Status:** 🔴 **BROKEN FOR PRODUCTION** — Clips disappear on redeploy

---

## 8. DOWNLOAD/COPY-LINK: Functionality

**Download Endpoint** (clips.py:787-808):
```python
@router.get("/download/{clip_id:int}")
def download_clip(clip_id: int, ...):
    # 1. Check auth (streamer only)
    # 2. Query clip from DB by ID + streamer_id
    # 3. Check file exists (os.path.exists)
    # 4. Return FileResponse with filename
```
- ✅ **Works end-to-end** (frontend calls it, backend returns file)
- ✅ **Auth gated** (streamer only, scoped to their clips)
- ✅ **Filename set** (based on clip title)

**Stream Endpoint** (clips.py:719-784):
```python
@router.get("/stream/{clip_id:int}")
def stream_clip(clip_id: int, ...):
    # 1. Check auth
    # 2. Query clip
    # 3. Check file exists
    # 4. Handle HTTP Range requests (for seeking)
    # 5. Return StreamingResponse
```
- ✅ **Works end-to-end** (video player streams from it)
- ✅ **Range support** (video player can seek)
- ✅ **Auth gated**

**Copy-Link** (frontend clips.js:170-183):
```jsx
const copyLink = async (clip) => {
  const url = `${window.location.origin}/api/clips/download/${clip.id}`;
  await navigator.clipboard.writeText(url);
}
```
- ✅ **Works** (copies full URL to clipboard)
- ⚠️ **Not authenticated** (URL includes clip ID only, no token)
  - Anyone with the URL can download
  - This is by design (share-friendly) or a security issue?

**Status:** ✅ **WORKING** (download + stream functional, copy-link works but unauthenticated)

---

## Summary Table

| # | Area | Status | Details |
|---|------|--------|---------|
| 1 | Thumbnails (backend) | 🔴 NOT BUILT | Column exists, never populated |
| 2 | ffmpeg available | ✅ YES | Already used for transcoding |
| 3 | Clip cards (frontend) | 🟡 PARTIAL | Structure there, needs thumbnails + duration |
| 4 | API fields | ✅ COMPLETE | All data provided; not all rendered |
| 5 | Empty/loading states | 🟡 BASIC | Exist but minimal styling/animation |
| 6 | File storage path | 🔴 EPHEMERAL | Ephemeral container disk (no Volume) |
| 7 | DB vs file persistence | 🔴 BROKEN | DB records survive; MP4s deleted on redeploy |
| 8 | Download/copy-link | ✅ WORKING | Fully functional |

---

## Recommended Minimal Changes (Phase 2)

### **First Frame Thumbnails** (~1 hr)
```
- Add extract_thumbnail(input_video) → thumbnail.jpg using ffmpeg
- Call on clip ingest (after transcode check)
- Save to: backend/data/clips/{uuid}_thumb.jpg
- Update Clip.thumbnail_path in DB
- Frontend renders: <img src={clip.thumbnail_url} />
```

### **Card Metadata Display** (~30 min)
```
- Display duration_seconds on card (already in API)
- Show relative time ("2 hours ago" vs full timestamp)
- Optional: Add view count when it's available
```

### **Empty/Loading Polish** (~30 min)
```
- Add spinner animation to loading state
- Add subtle gradient or icon to empty state
- Better responsive spacing
```

### **Persistent File Storage** (~2 hrs, optional for MVP)
```
- Option A: Add Railway Volume to Dockerfile
- Option B: Use S3 for clip storage (new dependency)
- Option C: Live with ephemeral for MVP, fix in Phase 3
```

### **Priority Order:**
1. **First-frame thumbnails** (core feature, uses existing ffmpeg)
2. **Card metadata** (polish, zero backend work)
3. **Empty/loading states** (polish, frontend only)
4. **Persistent storage** (infrastructure, can defer)

---

## Questions for Implementation

1. Should copy-link URLs be authenticated (include token) or public-shareable?
2. Should we use S3 now or defer persistent storage?
3. Should thumbnails be extracted on ingest or lazy-loaded on first view?
4. Should we rename "thumbnail_path" to "thumbnail_url" in API response?

---

**END OF AUDIT**  
All findings verified. Ready to implement when approved.
