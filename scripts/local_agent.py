import os
import time
import json
import hmac
import hashlib
import requests
import asyncio
import websockets
from obsws_python import ReqClient


API_BASE = os.getenv("KAZUMI_API_BASE", "http://localhost:8000")
STREAMER_ID = os.getenv("STREAMER_ID")
AGENT_ACCESS_KEY = os.getenv("AGENT_ACCESS_KEY", "")
AGENT_SIGNING_KEY = os.getenv("AGENT_SIGNING_KEY", "")
AGENT_POLL_INTERVAL = float(os.getenv("AGENT_POLL_INTERVAL", "0.5"))
AGENT_WS = os.getenv("AGENT_WS", "true").lower() == "true"

OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = int(os.getenv("OBS_PORT", "4455"))
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")
OBS_MIC_SOURCE = os.getenv("OBS_MIC_SOURCE", "Mic/Aux")


def sign_payload(payload: dict) -> str:
    message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(AGENT_SIGNING_KEY.encode(), message, hashlib.sha256).hexdigest()

def connect_obs():
    try:
        client = ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
        print(f"[Agent] Connected to OBS at {OBS_HOST}:{OBS_PORT}")
        return client
    except Exception as exc:
        print(f"[Agent] OBS connection failed: {exc}")
        return None

def execute_obs(client: ReqClient, action: str, payload: dict) -> tuple[bool, str]:
    if not client:
        return False, "OBS not connected"

    try:
        if action == "switch_scene":
            scene = payload.get("scene")
            if not scene:
                return False, "scene required"
            client.set_current_program_scene(scene)
            return True, f"Switched to {scene}"

        if action == "start_recording":
            client.start_record()
            return True, "Recording started"

        if action == "stop_recording":
            client.stop_record()
            return True, "Recording stopped"

        if action == "start_streaming":
            client.start_stream()
            return True, "Stream started"

        if action == "stop_streaming":
            client.stop_stream()
            return True, "Stream stopped"

        if action == "mute_mic":
            client.set_input_mute(OBS_MIC_SOURCE, True)
            return True, "Mic muted"

        if action == "unmute_mic":
            client.set_input_mute(OBS_MIC_SOURCE, False)
            return True, "Mic unmuted"

        if action == "save_replay_buffer":
            client.save_replay_buffer()
            return True, "Replay buffer saved"

        return False, f"Unknown action {action}"
    except Exception as exc:
        return False, str(exc)


def _escape_drawtext(text: str) -> str:
    return text.replace(":", r"\:").replace("'", r"\'")


def run_ffmpeg(input_path: str, output_path: str, *, watermark_text: str | None = None, subtitles_path: str | None = None) -> tuple[bool, str]:
    try:
        import subprocess
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        filters = [
            "scale=1080:1920:force_original_aspect_ratio=decrease",
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        ]
        if subtitles_path:
            filters.append(f"subtitles='{subtitles_path}'")
        if watermark_text:
            safe_text = _escape_drawtext(watermark_text)
            filters.append(
                "drawtext=text='{}':fontcolor=white:fontsize=42:box=1:boxcolor=black@0.4:boxborderw=12:x=40:y=40".format(safe_text)
            )
        vf = ",".join(filters)
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-vf", vf,
            "-t", "30",
            output_path,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "Export created"
    except Exception as exc:
        return False, str(exc)


def main():
    if not STREAMER_ID:
        raise SystemExit("STREAMER_ID is required")
    if not AGENT_ACCESS_KEY or not AGENT_SIGNING_KEY:
        raise SystemExit("AGENT_ACCESS_KEY and AGENT_SIGNING_KEY are required")

    headers = {"X-Agent-Key": AGENT_ACCESS_KEY}
    obs_client = connect_obs()

    async def ws_loop():
        ws_base = API_BASE.replace("https://", "wss://").replace("http://", "ws://")
        url = f"{ws_base}/agent/ws?streamer_id={STREAMER_ID}&key={AGENT_ACCESS_KEY}"
        while True:
            try:
                async with websockets.connect(url, ping_interval=10, ping_timeout=10) as websocket:
                    print("[Agent] WebSocket connected")
                    await websocket.send("ready")
                    async for raw in websocket:
                        data = json.loads(raw)
                        cmd = data.get("command") or {}
                        signature = data.get("signature", "")
                        expected = sign_payload(cmd)
                        if not hmac.compare_digest(signature, expected):
                            print("Signature mismatch. Skipping command.")
                            continue
                        print(f"[Agent] Received command: {cmd.get('action')} payload={cmd.get('payload')}")
                        action = cmd.get("action")
                        payload = cmd.get("payload") or {}
                        if action == "export_short_form":
                            ok, message = run_ffmpeg(
                                payload.get("input_path", ""),
                                payload.get("output_path", ""),
                                watermark_text=payload.get("watermark_text"),
                                subtitles_path=payload.get("subtitles_path"),
                            )
                        else:
                            ok, message = execute_obs(obs_client, action, payload)
                        requests.post(
                            f"{API_BASE}/agent/commands/{cmd.get('id')}/ack",
                            headers=headers,
                            json={"status": "executed" if ok else "error", "message": message},
                            timeout=10,
                        )
            except Exception as exc:
                print(f"[Agent] WS error: {exc}")
                await asyncio.sleep(AGENT_POLL_INTERVAL)

    def poll_loop():
        while True:
            try:
                res = requests.get(
                    f"{API_BASE}/agent/commands/next",
                    headers=headers,
                    params={"streamer_id": STREAMER_ID},
                    timeout=10,
                )
                data = res.json()
                if data.get("status") != "ok":
                    time.sleep(AGENT_POLL_INTERVAL)
                    continue

                cmd = data.get("command") or {}
                signature = data.get("signature", "")
                expected = sign_payload(cmd)
                if not hmac.compare_digest(signature, expected):
                    print("Signature mismatch. Skipping command.")
                    time.sleep(AGENT_POLL_INTERVAL)
                    continue

                print(f"[Agent] Received command: {cmd.get('action')} payload={cmd.get('payload')}")
                action = cmd.get("action")
                payload = cmd.get("payload") or {}
                if action == "export_short_form":
                    ok, message = run_ffmpeg(
                        payload.get("input_path", ""),
                        payload.get("output_path", ""),
                        watermark_text=payload.get("watermark_text"),
                        subtitles_path=payload.get("subtitles_path"),
                    )
                else:
                    ok, message = execute_obs(obs_client, action, payload)

                requests.post(
                    f"{API_BASE}/agent/commands/{cmd.get('id')}/ack",
                    headers=headers,
                    json={"status": "executed" if ok else "error", "message": message},
                    timeout=10,
                )
            except Exception as exc:
                print(f"[Agent] Error: {exc}")
                time.sleep(AGENT_POLL_INTERVAL)

    if AGENT_WS:
        asyncio.run(ws_loop())
    else:
        poll_loop()


if __name__ == "__main__":
    main()
