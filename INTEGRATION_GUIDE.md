# OBS Integration + Clip Generation Guide

## Architecture Overview

```
REAL-TIME STREAMING PIPELINE
├─ OBS Audio Polling (500ms intervals)
│  └─ Sends audio peak to Moment Detector
├─ Chat Events (from Twitch/YouTube/etc)
│  └─ Sends chat messages to Moment Detector
├─ Moment Detection (combines signals)
│  └─ Triggers when both audio + chat spikes detected
└─ Clip Generation (full video pipeline)
   ├─ Extract: OBS Replay Buffer → FFmpeg
   ├─ Transcribe: Audio → Word timestamps (Whisper)
   ├─ Recrop: Auto-crop to 9:16 vertical
   ├─ Caption: Add animated subtitles
   ├─ Label: Groq generates title + hashtags
   └─ Publish: Queue to TikTok/Shorts/Reels
```

## Setup Requirements

### 1. OBS Configuration
- **Replay Buffer**: Enable in OBS Settings → Output → Recording
- **WebSocket Server**: Enable OBS Studio Tools → WebSocket Server (default port 4455)
- **Connection**: Backend connects to `localhost:4455`

### 2. FFmpeg Installation (for actual clip extraction)
```bash
# Windows
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

### 3. Chat Integration (Twitch/YouTube)
- Twitch: Connect via OAuth token
- YouTube: Connect via API key
- Channels to monitor configured in Streamer Settings

### 4. Environment Variables
```env
OBS_WEBSOCKET_URL=ws://localhost:4455
OBS_WEBSOCKET_PASSWORD=your_password_if_set
GROQ_API_KEY=your_groq_api_key
FFMPEG_PATH=/path/to/ffmpeg  # Optional, auto-detected if in PATH
```

## How It Works

### Phase 1: Real-Time Detection
```
1. OBSAudioPoller polls OBS every 500ms
   - Estimates audio peak from stream bitrate
   - Sends audio event to Moment Detector if peak > 0.5

2. Chat Monitor listens to Twitch/YouTube chat
   - Counts messages per second
   - Sends chat event to Moment Detector on spike

3. Moment Detector combines signals
   - Chat velocity threshold: 5 msg/s (adjustable by sensitivity)
   - Audio peak threshold: 0.6 (adjustable by sensitivity)
   - Requires BOTH to trigger moment
   - 30-second debounce between moments
```

### Phase 2: Clip Generation (on moment detected)
```
1. ClipGeneratorService.on_moment_detected() called
   - Passes moment data to ClipPipeline

2. ClipPipeline.extract_clip_segment()
   - Accesses OBS replay buffer
   - Uses FFmpeg to cut 45-second segment
   - Saves as MP4 with H.264 + AAC

3. Database Update
   - Saves clip metadata with actual file path
   - Status: "pending" (waiting for post-processing)
   - Requested by: "auto_detection" (Kazumee AI)
   - Quality score: Normalized moment score (0-100%)

4. Optional Post-Processing (stages 2-6)
   - Transcribe audio with Whisper
   - Recrop to vertical format (9:16)
   - Add captions with word-level sync
   - Generate title/hashtags with Groq
   - Auto-publish to TikTok/Shorts/Reels
```

### Phase 3: User Interaction
```
1. Dashboard displays "CLIPS GENERATED" stat
   - Real-time update via WebSocket

2. Clips page shows pending auto-clips
   - Can share (copy link)
   - Can download (saves MP4)
   - Can export (queue to platforms)
   - Can delete

3. Settings control detection behavior
   - Sensitivity slider (0-100%)
   - Auto-publish toggle + platform selection
   - Minimum quality score threshold
```

## API Endpoints

### Moment Detection
- `POST /api/moments/chat-event` - Register chat message
- `POST /api/moments/audio-event` - Register audio peak
- `GET /api/moments/status` - Get detector status
- `POST /api/moments/test` - Simulate moment
- `POST /api/moments/reset` - Reset detector buffers
- `WS /api/moments/ws/updates` - Real-time updates

### Clip Management
- `GET /api/clips/pending` - Get processing clips
- `GET /api/clips/recent` - Get published clips
- `DELETE /api/clips/{id}` - Delete clip
- `POST /api/clips/{id}/export` - Queue export
- `GET /api/clips/{id}` - Get clip details

## Sensitivity Configuration

Sensitivity slider (0-100%) adjusts detection thresholds:

```python
# Formula: threshold = base_threshold * (1.0 - sensitivity)

Chat Threshold:
  - 0% sensitivity: 5 msg/s
  - 50% sensitivity: 2.5 msg/s
  - 100% sensitivity: 0.5 msg/s

Audio Threshold:
  - 0% sensitivity: 0.6 peak
  - 50% sensitivity: 0.3 peak
  - 100% sensitivity: 0.06 peak
```

Presets:
- **Conservative**: Detects only major highlights
- **Balanced**: Good mix of false positives vs misses
- **Aggressive**: Captures most entertaining moments

## Troubleshooting

### OBS Connection Failed
```
⚠ OBS Audio Poller failed: Connection refused
```
→ Ensure OBS is running and WebSocket Server enabled

### FFmpeg Not Found
```
⚠ Clip Generator Service failed: ffmpeg not found
```
→ Install FFmpeg or set FFMPEG_PATH environment variable

### No Clips Generated
1. Check OBS is connected: `curl http://localhost:8000/api/obs/status`
2. Check detector is running: `curl http://localhost:8000/api/moments/status`
3. Verify chat/audio events being received
4. Check backend logs for pipeline errors

### Clips Not Saved to Database
→ Database connection issue or replay buffer not available
→ Will fall back to simple DB insert with placeholder path

## Performance Notes

- **Audio Polling**: 500ms interval = 2 checks/sec (low CPU impact)
- **Moment Detection**: O(1) signal buffering, minimal memory
- **Clip Extraction**: Heavy (FFmpeg CPU usage), runs async
- **WebSocket Broadcasting**: Real-time updates to all connected clients
- **Database Queries**: Indexed by status + created_at for fast pagination

## Next Steps

1. **Real Stream Testing**: Test with actual Twitch/YouTube stream
2. **Transcription Integration**: Enable Whisper for automatic captions
3. **Auto-Publishing**: Wire YouTube Shorts/TikTok upload
4. **Analytics**: Track detection accuracy vs manual clip creation
5. **Mobile App**: Build iOS/Android client with real-time alerts
