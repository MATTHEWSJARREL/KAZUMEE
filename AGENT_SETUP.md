# Kazumee Autonomous Agent Setup

This is the live-clipping agent that runs on your streaming PC. It connects your OBS to Kazumee cloud.

## What It Does

1. **Connects to your local OBS** → Monitors replay buffer
2. **Waits for hype moment detection** → Cloud detects high-energy streams
3. **Captures replay buffer** → When moment fires, saves last 30-60s of video
4. **Uploads to Kazumee** → Clip goes to cloud for processing/export
5. **Exports to TikTok/YouTube** → Automatically posts to your social media

## One-Time OBS Setup (2 steps)

### Step 1: Enable WebSocket Server

1. Open OBS
2. Go to **Tools** → **WebSocket Server Settings**
3. Check **"Enable WebSocket server"**
4. Note the password (you'll need it below)

### Step 2: Enable Replay Buffer

1. Go to **Settings** → **Output**
2. Check **"Replay Buffer"** checkbox
3. Set **Replay Buffer Maximum Megabytes**: 500-1000 MB (depends on your bitrate)
4. Set **Replay Buffer Duration**: 30-60 seconds (recommended: 60s)
5. Click **OK**

That's it. You only do this once.

## Install & Run Agent

### 1. Install Python

Make sure you have Python 3.8+ installed:

```bash
python --version
```

### 2. Install Dependencies

```bash
pip install obsws-python websocket-client requests
```

### 3. Get Your Streamer Token

1. Go to https://kazumee.vercel.app
2. Log in with your Kazumee account
3. Go to **Settings** → **Agent Token**
4. Copy your token (looks like: `streamer_abc123xyz...`)

### 4. Run the Agent

**Option A: Set token via environment variable (recommended)**

```bash
# macOS / Linux
export STREAMER_TOKEN="your_token_here"
python kazumee-agent.py

# Windows PowerShell
$env:STREAMER_TOKEN="your_token_here"
python kazumee-agent.py

# Windows CMD
set STREAMER_TOKEN=your_token_here
python kazumee-agent.py
```

**Option B: Inline (one-liner)**

```bash
STREAMER_TOKEN="your_token_here" python kazumee-agent.py
```

### 5. Verify It's Running

You should see:

```
[ OK ] OBS connected (OBS 30.0.2)
[ OK ] Replay Buffer is running
[ OK ] Connected to Kazumee cloud ✓
[ OK ] Agent ready - waiting for hype moments...
```

**Green lights = ready!** Keep this terminal open while you stream.

---

## How It Works During a Stream

1. **You go live** on Twitch/YouTube
2. **Kazumee monitors your chat** (high energy, emotes, etc.)
3. **Hype moment detected** → Cloud sends signal to your PC
4. **Agent saves replay buffer** → Last 60s of your stream saved as MP4
5. **Clip uploads** → File goes to Kazumee cloud
6. **Processing** → Kazumee analyzes, adds captions, optimizes quality
7. **Auto-export** → Clip posted to TikTok/YouTube/Instagram

**Total time**: Moment → Clip ready for export: ~30-60 seconds

---

## Troubleshooting

### "Can't reach OBS on localhost:4455"

**Solution**: 
1. Make sure OBS is open
2. Go to Tools → WebSocket Server Settings
3. Check "Enable WebSocket server"
4. Restart OBS if it doesn't work

### "STREAMER_TOKEN not set"

**Solution**:
1. Copy your token from https://kazumee.vercel.app/settings
2. Export it: `export STREAMER_TOKEN="your_token"`
3. Run the agent: `python kazumee-agent.py`

### "Replay Buffer not running"

**Solution**:
1. Go to OBS Settings → Output
2. Check "Replay Buffer" checkbox
3. Set duration to 60 seconds
4. Click OK
5. Restart the agent

### "Upload failed (401)"

**Solution**: Your token expired or is invalid.
1. Log back into https://kazumee.vercel.app
2. Go to Settings → regenerate token
3. Update your STREAMER_TOKEN environment variable
4. Restart the agent

### "Connection closed"

This is normal if:
- You restart OBS
- Internet hiccup
- You stop streaming

The agent automatically reconnects. Just wait ~5 seconds and it should say "Connected to Kazumee cloud ✓" again.

---

## Advanced Options

You can customize OBS host/port if needed:

```bash
STREAMER_TOKEN="..." OBS_HOST="192.168.1.100" OBS_PORT="4455" python kazumee-agent.py
```

Or create a `.env` file:

```
STREAMER_TOKEN=your_token_here
OBS_HOST=localhost
OBS_PORT=4455
CLOUD_WS_URL=wss://kazumee-production.up.railway.app/ws/agent
INGEST_URL=https://kazumee-production.up.railway.app/api/clips/ingest
```

Then just run: `python kazumee-agent.py`

---

## Keep It Running

The agent needs to run **while you're streaming**. Options:

1. **Keep terminal open** (simplest)
2. **Run in background** (macOS/Linux):
   ```bash
   nohup python kazumee-agent.py > kazumee.log 2>&1 &
   ```
3. **Schedule to start on boot** (Windows Task Scheduler or macOS LaunchAgent)
4. **Docker** (for advanced users)

---

## Support

Having issues? Check:
1. Agent logs above
2. Your Kazumee dashboard: https://kazumee.vercel.app/monitoring
3. OBS WebSocket is enabled
4. Replay Buffer is enabled with 60s duration
5. Your token is valid and hasn't expired

---

**You're ready!** Go live and let Kazumee capture your moments 🚀
