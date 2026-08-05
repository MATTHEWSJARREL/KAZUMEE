#!/usr/bin/env python3
"""
Kazumee Live-Clipping Agent
============================

Runs on the streamer's PC. Connects to:
1. Local OBS (obs-websocket v5)
2. Kazumee cloud backend (WebSocket)

When cloud detects a hype moment, it sends {"cmd": "clip"} → agent saves OBS replay buffer.

Setup:
1. pip install obsws-python websocket-client requests
2. Set environment variables (see CONFIG below)
3. python kazumee-agent.py

OBS Setup (one-time):
- Tools → WebSocket Server Settings → Enable WebSocket Server
- Settings → Output → Replay Buffer → Buffer enabled + duration (60s recommended)
"""

import os
import json
import time
import threading
import sys

try:
    import obsws_python as obs
    import websocket
    import requests
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
except ImportError:
    print("[FAIL] Missing dependencies. Run:")
    print("  pip install obsws-python websocket-client requests pystray pillow")
    sys.exit(1)


# ==============================================================================
# CONFIGURATION
# ==============================================================================

OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = int(os.getenv("OBS_PORT", "4455"))
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")

CLOUD_WS_URL = os.getenv("CLOUD_WS_URL", "wss://kazumee-production.up.railway.app/ws/agent")
INGEST_URL = os.getenv("INGEST_URL", "https://kazumee-production.up.railway.app/api/clips/ingest")

STREAMER_TOKEN = os.getenv("STREAMER_TOKEN", "")  # Get from Kazumee dashboard

RECONNECT_SECS = 5
TOKEN_STORAGE_FILE = os.path.expanduser("~/.kazumee_agent_token")
AUTH_SERVER_PORT = 9284


# ==============================================================================
# TOKEN MANAGEMENT
# ==============================================================================

def load_token():
    """Load saved token from disk."""
    if os.path.exists(TOKEN_STORAGE_FILE):
        try:
            with open(TOKEN_STORAGE_FILE, 'r') as f:
                return f.read().strip()
        except:
            pass
    return None

def save_token(token):
    """Save token to disk."""
    try:
        with open(TOKEN_STORAGE_FILE, 'w') as f:
            f.write(token)
    except Exception as e:
        status("err", f"Failed to save token: {e}")

def open_login_in_browser():
    """Open browser to login page."""
    import webbrowser
    login_url = f"https://kazumee.vercel.app/auth?redirect=http://127.0.0.1:{AUTH_SERVER_PORT}/auth-callback"
    webbrowser.open(login_url)
    status("info", "Opening login page in browser...")


# ==============================================================================
# LOCALHOST AUTH SERVER
# ==============================================================================

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json

auth_server_ready = threading.Event()

class AuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth redirect from browser."""

    def do_GET(self):
        """Handle GET /auth-callback?token=..."""
        parsed = urlparse(self.path)
        if parsed.path == '/auth-callback':
            query = parse_qs(parsed.query)
            token = query.get('token', [None])[0]

            if token:
                global STREAMER_TOKEN
                STREAMER_TOKEN = token
                save_token(token)
                status("ok", f"Token saved successfully!")

                # Return success page
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html = """
                    <html>
                    <head><title>Kazumee Agent - Connected</title></head>
                    <body style="font-family: Arial; text-align: center; padding: 50px;">
                        <h2>[SUCCESS] Connected!</h2>
                        <p>Your Kazumee Agent is now connected.</p>
                        <p>You can close this window and return to the agent.</p>
                    </body>
                    </html>
                """
                self.wfile.write(html.encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"<h2>[ERROR] No token received</h2>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress server logs

def start_auth_server():
    """Start localhost auth server."""
    try:
        server = HTTPServer(('127.0.0.1', AUTH_SERVER_PORT), AuthCallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        status("info", "Auth server started on http://127.0.0.1:9284")
        return server
    except Exception as e:
        status("err", f"Failed to start auth server: {e}")
        return None


# ==============================================================================
# SYSTEM TRAY ICON
# ==============================================================================

def create_tray_icon(is_connected=False):
    """Create system tray icon."""
    size = 64
    image = Image.new('RGB', (size, size), color='black')
    draw = ImageDraw.Draw(image)

    # Draw circle (green if connected, red if not)
    color = '#00ff00' if is_connected else '#ff0000'
    draw.ellipse([10, 10, size-10, size-10], fill=color)

    return image

def setup_tray_icon(on_quit, on_login=None):
    """Setup system tray icon with menu."""
    menu_items = []

    if on_login:
        menu_items.append(MenuItem('Login', on_login))
        menu_items.append(MenuItem('-', None))

    menu_items.append(MenuItem('Quit', on_quit))

    icon = Icon(
        "Kazumee Agent",
        image=create_tray_icon(is_connected=False),
        menu=Menu(*menu_items)
    )

    return icon


# ==============================================================================
# STATUS PRINTER
# ==============================================================================

def status(kind, msg):
    """Print colored status messages."""
    marks = {
        "ok": "\033[92m[ OK ]\033[0m",
        "warn": "\033[93m[WARN]\033[0m",
        "err": "\033[91m[FAIL]\033[0m",
        "info": "\033[96m[ .. ]\033[0m"
    }
    mark = marks.get(kind, "[    ]")
    print(f"{mark} {msg}", flush=True)


# ==============================================================================
# OBS SIDE
# ==============================================================================

class OBSSide:
    def __init__(self):
        self.req = None
        self.ev = None
        self.ready = False

    def connect(self):
        """Connect to OBS and ensure replay buffer is running."""
        while True:
            try:
                self.req = obs.ReqClient(
                    host=OBS_HOST,
                    port=OBS_PORT,
                    password=OBS_PASSWORD,
                    timeout=3
                )
                v = self.req.get_version()
                status("ok", f"OBS connected ({v.obs_version})")

                self._ensure_replay_buffer()
                self._wire_events()
                self.ready = True
                return

            except Exception as e:
                status("err", f"Can't reach OBS on {OBS_HOST}:{OBS_PORT}")
                status("err", "Make sure: (1) OBS is open, (2) Tools → WebSocket Server Settings is ENABLED")
                status("info", f"Retrying in {RECONNECT_SECS}s... ({type(e).__name__})")
                time.sleep(RECONNECT_SECS)

    def _ensure_replay_buffer(self):
        """Start replay buffer if it's not running."""
        try:
            st = self.req.get_replay_buffer_status()
            if st.output_active:
                status("ok", "Replay Buffer is running")
            else:
                self.req.start_replay_buffer()
                status("ok", "Started Replay Buffer for you")
        except Exception as e:
            status("warn", f"Couldn't check replay buffer: {e}")

    def _wire_events(self):
        """Listen for replay buffer saved events."""
        try:
            self.ev = obs.EventClient(
                host=OBS_HOST,
                port=OBS_PORT,
                password=OBS_PASSWORD
            )

            def on_replay_buffer_saved(data):
                path = data.saved_replay_path
                status("ok", f"Clip saved by OBS: {path}")
                # Upload in background thread
                threading.Thread(
                    target=upload_clip,
                    args=(path,),
                    daemon=True
                ).start()

            self.ev.callback.register(on_replay_buffer_saved)
            status("ok", "Event listener ready")

        except Exception as e:
            status("err", f"Couldn't wire events: {e}")

    def trigger_clip(self):
        """Tell OBS to save the replay buffer."""
        if not self.ready or self.req is None:
            status("warn", "OBS not connected, clip skipped")
            return

        try:
            self.req.save_replay_buffer()
            status("info", "Hype moment → saving replay buffer...")
        except Exception as e:
            status("err", f"Failed to save replay buffer: {e}")


# ==============================================================================
# UPLOAD CLIP TO CLOUD
# ==============================================================================

def upload_clip(path):
    """Upload finished clip to cloud."""
    try:
        if not os.path.exists(path):
            status("err", f"Clip file not found: {path}")
            return

        file_size = os.path.getsize(path)
        status("info", f"Uploading {file_size / 1024 / 1024:.1f} MB...")

        with open(path, "rb") as f:
            r = requests.post(
                INGEST_URL,
                headers={"Authorization": f"Bearer {STREAMER_TOKEN}"},
                files={"clip": (os.path.basename(path), f, "video/mp4")},
                data={"ts": time.time(), "source": "auto"},
                timeout=300,  # 5 minutes for upload
            )

        if r.ok:
            clip_id = r.json().get("id", "unknown")
            status("ok", f"Clip uploaded! ID: {clip_id}")
        else:
            status("err", f"Upload failed ({r.status_code}): {r.text[:200]}")

    except Exception as e:
        status("err", f"Upload error: {e}")


# ==============================================================================
# CLOUD SIDE
# ==============================================================================

class CloudSide:
    def __init__(self, obs_side: OBSSide):
        self.obs = obs_side

    def run_forever(self):
        """Hold WebSocket connection to cloud forever."""
        while True:
            try:
                ws = websocket.WebSocketApp(
                    CLOUD_WS_URL,
                    header=[f"Authorization: Bearer {STREAMER_TOKEN}"],
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_close=self._on_close,
                    on_error=self._on_error,
                )
                ws.run_forever(ping_interval=20, ping_timeout=10)

            except Exception as e:
                status("err", f"Cloud connection error: {e}")

            status("info", f"Reconnecting in {RECONNECT_SECS}s...")
            time.sleep(RECONNECT_SECS)

    def _on_open(self, ws):
        status("ok", "Connected to Kazumee cloud ✓")
        status("ok", "Agent ready - waiting for hype moments...")
        ws.send(json.dumps({"type": "agent_online"}))

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except ValueError:
            return

        if data.get("cmd") == "clip":
            status("info", "🔴 HYPE MOMENT DETECTED - capturing clip...")
            self.obs.trigger_clip()
        elif data.get("cmd") == "ping":
            ws.send(json.dumps({"type": "pong"}))

    def _on_close(self, ws, code, reason):
        status("warn", "Cloud connection closed")

    def _on_error(self, ws, error):
        status("err", f"Cloud error: {error}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    global STREAMER_TOKEN

    print("\n" + "=" * 60)
    print("  KAZUMEE LIVE-CLIPPING AGENT")
    print("=" * 60 + "\n")

    # Try to load saved token first
    if not STREAMER_TOKEN:
        STREAMER_TOKEN = load_token()

    # If still no token, start auth flow
    if not STREAMER_TOKEN:
        status("info", "No token found. Starting login...")
        auth_server = start_auth_server()
        time.sleep(0.5)
        open_login_in_browser()
        status("info", "Waiting for authentication...")

        # Wait up to 60 seconds for token
        for i in range(60):
            if STREAMER_TOKEN:
                break
            time.sleep(1)

        if not STREAMER_TOKEN:
            status("err", "Authentication timeout. Please run again.")
            sys.exit(1)

    status("ok", "Authenticated!")
    status("info", f"OBS: {OBS_HOST}:{OBS_PORT}")
    status("info", f"Cloud: {CLOUD_WS_URL}")

    # Connect to OBS in background
    obs_side = OBSSide()
    threading.Thread(target=obs_side.connect, daemon=True).start()

    # Give OBS a moment to connect
    time.sleep(1)

    # Hold cloud connection on main thread
    try:
        CloudSide(obs_side).run_forever()
    except KeyboardInterrupt:
        status("info", "Shutting down. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
