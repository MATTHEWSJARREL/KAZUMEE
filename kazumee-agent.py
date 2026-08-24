#!/usr/bin/env python3

# CRITICAL: Redirect stdout/stderr FIRST, before any imports or docstring
# Under --windowed mode, sys.stdout/sys.stderr are None, causing silent crashes
# NOTE: Open in "w" mode to reset log on each launch (don't append forever)
import sys, os
if sys.stdout is None or sys.stderr is None:
    _log = open(os.path.join(os.path.expanduser("~"), "kazumee_agent.log"), "w")
    if sys.stdout is None: sys.stdout = _log
    if sys.stderr is None: sys.stderr = _log

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

import json
import time
import threading
import ssl
import urllib3

# Suppress SSL warnings (Railway cert expired; test-only workaround)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

# Optional: Try to import pynput for global hotkeys
try:
    from pynput import keyboard
    HAS_HOTKEY_SUPPORT = True
except ImportError:
    HAS_HOTKEY_SUPPORT = False


# ==============================================================================
# CONFIGURATION
# ==============================================================================

OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = int(os.getenv("OBS_PORT", "4455"))
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")

CLOUD_WS_URL = os.getenv("CLOUD_WS_URL", "wss://kazumee-production.up.railway.app/api/ws/agent")
INGEST_URL = os.getenv("INGEST_URL", "https://kazumee-production.up.railway.app/api/clips/ingest")

STREAMER_TOKEN = None
OBS_PASSWORD = None

RECONNECT_SECS = 5
CONFIG_FILE = os.path.expanduser("~/.kazumee_agent_config.json")
OLD_TOKEN_FILE = os.path.expanduser("~/.kazumee_agent_token")
AUTH_SERVER_PORT = 9284


# ==============================================================================
# CONFIG MANAGEMENT
# ==============================================================================

def load_config():
    """Load config from disk. Returns {streamer_token, obs_password} or None."""
    # Try new config file first
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                status("ok", f"Loaded config from {CONFIG_FILE}")
                return config
        except Exception as e:
            status("err", f"Failed to read config: {e}")
            return None

    # Fallback: migrate old token file
    if os.path.exists(OLD_TOKEN_FILE):
        try:
            with open(OLD_TOKEN_FILE, 'r') as f:
                token = f.read().strip()
                config = {"streamer_token": token, "obs_password": None}
                status("info", "Migrating old token file to new config format")
                save_config(config)
                return config
        except Exception as e:
            status("err", f"Failed to migrate old config: {e}")
            return None

    status("info", f"No config found at {CONFIG_FILE}")
    return None

def save_config(config):
    """Save config to disk with restricted permissions."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        # Set file permissions to 600 (user read/write only)
        os.chmod(CONFIG_FILE, 0o600)
        status("ok", f"Config saved to {CONFIG_FILE}")
        # Verify it was written
        if os.path.exists(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 0:
            status("ok", "Config file verified")
        else:
            status("err", "Config file not written or empty!")
    except Exception as e:
        status("err", f"Failed to save config: {e}")

def validate_token(token):
    """Validate token against backend. Returns True if valid."""
    try:
        backend_url = INGEST_URL.rsplit('/api/', 1)[0]  # https://kazumee-production.up.railway.app
        r = requests.post(
            f"{backend_url}/api/agent/token-verify",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
            verify=False
        )
        return r.status_code == 200
    except:
        return False

def run_setup_dialog():
    """Show tkinter dialog to collect token and OBS password. Returns config dict or None."""
    import tkinter as tk
    from tkinter import simpledialog, messagebox

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    # Get Kazumee token
    while True:
        token = simpledialog.askstring(
            "Kazumee Agent - Setup",
            "1. Paste your Kazumee agent token:\n\n(Get it from https://kazumee.vercel.app/settings)",
            show='*'
        )

        if token is None:  # User clicked Cancel
            return None

        token = token.strip()
        if not token:
            messagebox.showerror("Error", "Token cannot be empty")
            continue

        # Validate token
        if validate_token(token):
            break
        else:
            messagebox.showerror("Invalid Token", "Token is invalid or expired. Please try again.")
            continue

    # Get OBS WebSocket password
    obs_password = simpledialog.askstring(
        "Kazumee Agent - Setup",
        "2. Enter your OBS WebSocket password:\n\n(From OBS: Tools → WebSocket Server Settings → Show Connect Info)",
        show='*'
    )

    if obs_password is None:
        obs_password = ""  # Allow empty password if OBS has no auth

    config = {"streamer_token": token, "obs_password": obs_password}
    save_config(config)
    messagebox.showinfo("Setup Complete", f"Kazumee Agent is ready!\nConfig saved to:\n{CONFIG_FILE}\n\nThe agent will now start.")
    root.destroy()
    return config

def open_dashboard():
    """Open dashboard in browser."""
    import webbrowser
    webbrowser.open("https://kazumee.vercel.app/settings")


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
                # Load existing config or create new
                config = load_config() or {}
                config["streamer_token"] = token
                save_config(config)
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


# ==============================================================================
# TRAY ICON & STATUS TRACKING
# ==============================================================================

agent_status = {
    "obs_connected": False,
    "cloud_connected": False,
    "last_clip_time": None,
    "tray_icon": None,
}

def create_icon_image():
    """Create a circle icon reflecting current connection status."""
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Determine color based on status
    if agent_status["obs_connected"] and agent_status["cloud_connected"]:
        color = (76, 175, 80, 255)  # Green
    elif agent_status["obs_connected"] or agent_status["cloud_connected"]:
        color = (255, 193, 7, 255)  # Amber
    else:
        color = (244, 67, 54, 255)  # Red

    # Draw circle
    margin = 8
    draw.ellipse([margin, margin, size-margin, size-margin], fill=color)

    return image

def create_tray_icon():
    """Create system tray icon with status menu."""

    def on_quit():
        """Quit the application."""
        status("info", "Shutting down...")
        os._exit(0)

    def on_reenter_setup():
        """Re-enter setup (token + OBS password)."""
        config = run_setup_dialog()
        if config:
            global STREAMER_TOKEN, OBS_PASSWORD
            STREAMER_TOKEN = config.get("streamer_token")
            OBS_PASSWORD = config.get("obs_password", "")
            status("ok", "Setup updated!")

    # Build menu
    menu = Menu(
        MenuItem("Kazumee Agent", lambda: None, enabled=False),
        MenuItem("Open Dashboard", lambda: open_dashboard()),
        MenuItem("Re-enter setup", lambda: on_reenter_setup()),
        MenuItem("Quit", lambda: on_quit()),
    )

    # Create icon
    icon = Icon(
        name="Kazumee",
        icon=create_icon_image(),
        menu=menu,
        title="Kazumee Agent"
    )

    agent_status["tray_icon"] = icon
    return icon

def update_tray_icon():
    """Update tray icon to reflect current status."""
    if agent_status["tray_icon"]:
        try:
            agent_status["tray_icon"].icon = create_icon_image()
        except:
            pass  # Icon update not critical

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
# ==============================================================================
# STATUS PRINTER
# ==============================================================================

def status(kind, msg):
    """Print colored status messages (safely handle encoding)."""
    marks = {
        "ok": "\033[92m[ OK ]\033[0m",
        "warn": "\033[93m[WARN]\033[0m",
        "err": "\033[91m[FAIL]\033[0m",
        "info": "\033[96m[ .. ]\033[0m"
    }
    mark = marks.get(kind, "[    ]")
    text = f"{mark} {msg}"
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        # Fallback for --windowed mode with redirected stdout
        try:
            print(text.encode('ascii', 'replace').decode('ascii'), flush=True)
        except:
            pass  # Last resort: silently fail


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
                agent_status["obs_connected"] = True
                update_tray_icon()

                self._ensure_replay_buffer()
                self._wire_events()
                self.ready = True
                return

            except Exception as e:
                agent_status["obs_connected"] = False
                update_tray_icon()
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
                agent_status["last_clip_time"] = time.time()
                update_tray_icon()
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
    if not os.path.exists(path):
        status("err", f"Clip file not found: {path}")
        return

    file_size = os.path.getsize(path)
    status("info", f"Uploading {file_size / 1024 / 1024:.1f} MB...")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            with open(path, "rb") as f:
                r = requests.post(
                    INGEST_URL,
                    headers={"Authorization": f"Bearer {STREAMER_TOKEN}"},
                    files={"clip": (os.path.basename(path), f, "video/mp4")},
                    data={"ts": time.time(), "source": "auto"},
                    timeout=300,
                    verify=False,
                )

            if r.ok:
                clip_id = r.json().get("id", "unknown")
                status("ok", f"Clip uploaded! ID: {clip_id}")
                return
            else:
                status("err", f"Upload failed ({r.status_code}): {r.text[:200]}")
                return
        except Exception as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt
                status("info", f"Upload attempt {attempt}/{max_retries} failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                status("err", f"Upload error (attempt {attempt}/{max_retries}): {e}")


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
                # Skip SSL verification (Railway cert expired; test-only workaround)
                ssl_opts = {"cert_reqs": ssl.CERT_NONE, "check_hostname": False}

                ws = websocket.WebSocketApp(
                    CLOUD_WS_URL,
                    header=[f"Authorization: Bearer {STREAMER_TOKEN}"],
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_close=self._on_close,
                    on_error=self._on_error,
                )
                ws.run_forever(ping_interval=20, ping_timeout=10, sslopt=ssl_opts)

            except Exception as e:
                status("err", f"Cloud connection error: {e}")

            status("info", f"Reconnecting in {RECONNECT_SECS}s...")
            time.sleep(RECONNECT_SECS)

    def _on_open(self, ws):
        agent_status["cloud_connected"] = True
        update_tray_icon()
        status("ok", "Connected to Kazumee cloud [OK]")
        status("ok", "Agent ready - waiting for hype moments...")
        ws.send(json.dumps({"type": "agent_online"}))

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except ValueError:
            return

        # Handle clip command (old format: "cmd": "clip")
        if data.get("cmd") == "clip":
            status("info", "[CLIP] HYPE MOMENT DETECTED - capturing clip...")
            self.obs.trigger_clip()

        # Handle server keepalive ping (new format: "type": "ping")
        elif data.get("type") == "ping":
            status("debug", "Keepalive ping received from server")
            ws.send(json.dumps({"type": "pong"}))

        # Handle old ping format (fallback)
        elif data.get("cmd") == "ping":
            ws.send(json.dumps({"type": "pong"}))

    def _on_close(self, ws, code, reason):
        agent_status["cloud_connected"] = False
        update_tray_icon()
        status("warn", "Cloud connection closed")

    def _on_error(self, ws, error):
        agent_status["cloud_connected"] = False
        update_tray_icon()
        status("err", f"Cloud error: {error}")


# ==============================================================================
# GLOBAL HOTKEY LISTENER (OPTIONAL)
# ==============================================================================

hotkey_listener = None
obs_side_global = None  # Reference to OBSSide for hotkey handler

def setup_hotkey_listener(obs_side):
    """Start listening for global hotkey (Ctrl+Shift+C) to trigger clip."""
    if not HAS_HOTKEY_SUPPORT:
        status("warn", "pynput not installed - hotkey support disabled")
        status("info", "  To enable: pip install pynput")
        return

    global obs_side_global
    obs_side_global = obs_side

    def on_hotkey_press():
        status("info", "🎬 HOTKEY: Ctrl+Shift+C pressed - triggering clip...")
        try:
            obs_side_global.trigger_clip()
        except Exception as e:
            status("err", f"Hotkey clip failed: {e}")

    # Define hotkey combo
    from pynput.keyboard import Key, Controller, Listener

    hotkey_combo = {Key.ctrl_l, Key.shift_l, Key.c}
    current_keys = set()

    def on_press(key):
        try:
            current_keys.add(key)
            if hotkey_combo.issubset(current_keys):
                on_hotkey_press()
        except AttributeError:
            pass

    def on_release(key):
        try:
            current_keys.discard(key)
        except AttributeError:
            pass

    try:
        listener = Listener(on_press=on_press, on_release=on_release)
        listener.start()
        status("ok", "Global hotkey enabled: Ctrl+Shift+C to clip (no alt-tab needed)")
        return listener
    except Exception as e:
        status("warn", f"Failed to setup hotkey listener: {e}")
        return None


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    global STREAMER_TOKEN, OBS_PASSWORD

    print("\n" + "=" * 60)
    print("  KAZUMEE LIVE-CLIPPING AGENT")
    print("=" * 60 + "\n")

    # Load config (token + OBS password)
    config = load_config()

    # If no config or missing required fields, run setup dialog
    if not config or not config.get("streamer_token"):
        if config and not config.get("streamer_token"):
            status("info", "Config exists but missing token. Re-running setup.")
        else:
            status("info", "First run: please enter your credentials.")

        config = run_setup_dialog()

        if not config or not config.get("streamer_token"):
            status("err", "Setup cancelled or failed. Exiting.")
            sys.exit(1)

    STREAMER_TOKEN = config.get("streamer_token")
    OBS_PASSWORD = config.get("obs_password", "")

    if not STREAMER_TOKEN:
        status("err", "No valid token in config. Exiting.")
        sys.exit(1)

    status("ok", "Config loaded successfully")

    status("ok", "Authenticated!")
    status("info", f"OBS: {OBS_HOST}:{OBS_PORT}")
    status("info", f"Cloud: {CLOUD_WS_URL}")

    # Initialize OBS connection in background
    obs_side = OBSSide()
    obs_thread = threading.Thread(target=obs_side.connect, daemon=True)
    obs_thread.start()

    # Setup global hotkey listener (optional)
    global hotkey_listener
    hotkey_listener = setup_hotkey_listener(obs_side)

    # Start cloud connection in background
    def cloud_loop():
        try:
            CloudSide(obs_side).run_forever()
        except Exception as e:
            status("err", f"Cloud error: {e}")

    cloud_thread = threading.Thread(target=cloud_loop, daemon=False)
    cloud_thread.start()

    # Run tray icon on MAIN thread (required for pystray visibility)
    try:
        tray = create_tray_icon()
        tray.run()  # Blocking call on main thread
    except KeyboardInterrupt:
        status("info", "Shutting down. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
