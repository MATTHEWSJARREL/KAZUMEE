from datetime import datetime, timedelta, timezone
import json
import logging
import os
import platform
import secrets

from obsws_python import ReqClient

from backend.config import config
from backend.core.logger import get_logger


class OBSAdapter:
    def __init__(self):
        self.logger = get_logger(__name__)
        # obsws_python logs full tracebacks on connection failures by default.
        # Keep Kazumi logs clean when OBS is intentionally offline.
        for logger_name in (
            "obsws_python",
            "obsws_python.baseclient",
            "obsws_python.baseclient.ObsClient",
        ):
            obs_logger = logging.getLogger(logger_name)
            obs_logger.setLevel(logging.CRITICAL)
            obs_logger.propagate = False
        self.client = None
        self.connected = False
        self.reconnect_cooldown_sec = int(getattr(config, "obs_reconnect_cooldown_sec", 8) or 8)
        self._next_reconnect_at = datetime.min.replace(tzinfo=timezone.utc)
        self._last_connect_error = None
        self._last_stream_bytes = None
        self._last_stream_sample_at = None
        self._replay_buffer_auto_started = False

        # Attempt to pre-create OBS WebSocket config on first run
        self._ensure_obs_websocket_enabled()

        self._connect(initial=True)

    def _now_utc(self):
        return datetime.now(timezone.utc)

    def _ensure_obs_websocket_enabled(self):
        """
        Pre-create OBS WebSocket config to enable it before OBS launches.
        This removes the friction of manually enabling WebSocket in OBS settings.
        """
        try:
            # Construct path to OBS WebSocket config
            if platform.system() == "Windows":
                appdata = os.getenv("APPDATA")
                if not appdata:
                    self.logger.warning("[SETUP] APPDATA not set, skipping WebSocket config pre-creation")
                    return

                obs_websocket_dir = os.path.join(appdata, "obs-studio", "plugin_config", "obs-websocket")
                config_path = os.path.join(obs_websocket_dir, "config.json")
            else:
                # Linux/Mac support (simplified)
                home = os.path.expanduser("~")
                obs_websocket_dir = os.path.join(home, ".config", "obs-studio", "plugin_config", "obs-websocket")
                config_path = os.path.join(obs_websocket_dir, "config.json")

            # Check if OBS plugin directory exists
            if not os.path.exists(obs_websocket_dir):
                self.logger.info("[SETUP] OBS WebSocket plugin directory not found. OBS may not be installed or not launched yet.")
                self.logger.info(f"[SETUP] Once OBS launches, we'll enable WebSocket in: {obs_websocket_dir}")
                return

            # Read existing config or create new one
            existing_config = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        existing_config = json.load(f)
                except Exception as e:
                    self.logger.warning(f"[SETUP] Failed to read existing WebSocket config: {e}")
                    existing_config = {}

            # Merge with defaults (don't override existing values)
            websocket_config = {
                "alerts_enabled": existing_config.get("alerts_enabled", False),
                "auth_required": existing_config.get("auth_required", True),
                "first_load": existing_config.get("first_load", False),
                "server_enabled": True,  # ← ENABLE if not already
                "server_password": existing_config.get("server_password", config.obs_password or "kazumi123"),
                "server_port": existing_config.get("server_port", config.obs_port or 4455),
            }

            # Write config file
            os.makedirs(obs_websocket_dir, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(websocket_config, f, indent=2)

            if existing_config.get("server_enabled"):
                self.logger.info("[SETUP] WebSocket server already enabled in OBS config")
            else:
                self.logger.info(f"[SETUP] ✓ Pre-created OBS WebSocket config: {config_path}")
                self.logger.info(f"[SETUP]   - Server enabled: true")
                self.logger.info(f"[SETUP]   - Port: {websocket_config['server_port']}")
                self.logger.info(f"[SETUP]   - Password: {websocket_config['server_password']}")
                self.logger.info("[SETUP]   Note: Changes apply when OBS restarts")

        except Exception as e:
            self.logger.warning(f"[SETUP] Failed to pre-create WebSocket config: {e}")

    async def _auto_start_replay_buffer(self):
        """
        Auto-start the OBS Replay Buffer on successful connection.
        This removes the friction of manually enabling/starting it.
        """
        if not self.connected or not self.client or self._replay_buffer_auto_started:
            return

        try:
            # Check if replay buffer is already running
            status = await self.get_replay_buffer_status()
            if status.get("active"):
                self.logger.info("[SETUP] Replay Buffer already running")
                self._replay_buffer_auto_started = True
                return

            # Start the replay buffer
            result = await self.start_replay_buffer()
            if result.get("status") == "ok":
                self.logger.info("[SETUP] ✓ Replay Buffer auto-started successfully")
                self._replay_buffer_auto_started = True
            else:
                self.logger.warning(f"[SETUP] Failed to auto-start Replay Buffer: {result.get('reason')}")
        except Exception as e:
            self.logger.warning(f"[SETUP] Error auto-starting Replay Buffer: {e}")

    def _mark_retry_backoff(self):
        self._next_reconnect_at = self._now_utc() + timedelta(seconds=self.reconnect_cooldown_sec)

    def _mark_transport_error(self, error: Exception, context: str = "OBS connection issue"):
        self.connected = False
        self.client = None
        error_text = f"{type(error).__name__}: {error}"
        if error_text != self._last_connect_error:
            self.logger.warning(f"{context}: {error}")
        self._last_connect_error = error_text
        self._mark_retry_backoff()

    @staticmethod
    def _extract(obj, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    @staticmethod
    def _pick(obj, keys: tuple[str, ...], default=None):
        for key in keys:
            value = OBSAdapter._extract(obj, key, None)
            if value is not None:
                return value
        return default

    def _normalize_scene_item(self, item, input_kind_by_name: dict[str, str] | None = None):
        source_name = str(
            self._pick(item, ("sourceName", "source_name", "inputName", "input_name"), "")
        ).strip()
        source_kind = str(
            self._pick(item, ("inputKind", "input_kind", "sourceType", "source_type"), "")
        ).strip()
        if not source_kind and input_kind_by_name and source_name:
            source_kind = str(input_kind_by_name.get(source_name, "")).strip()
        return {
            "scene_item_id": self._safe_int(self._pick(item, ("sceneItemId", "scene_item_id"), 0), 0),
            "source_name": source_name,
            "source_type": source_kind or "unknown",
            "visible": bool(self._pick(item, ("sceneItemEnabled", "scene_item_enabled"), False)),
            "is_group": bool(self._pick(item, ("isGroup", "is_group"), False)),
        }

    def _is_camera_kind(self, source_type: str) -> bool:
        value = (source_type or "").strip().lower()
        return value in {"dshow_input", "av_capture_input", "v4l2_input"}

    def _current_scene_name(self) -> str:
        response = self.client.get_current_program_scene()
        return str(
            self._pick(response, ("current_program_scene_name", "scene_name", "currentProgramSceneName"), "Unknown")
        )

    def _input_kind_map(self) -> dict[str, str]:
        kinds: dict[str, str] = {}
        try:
            inputs_response = self.client.get_input_list()
        except TypeError:
            inputs_response = self.client.get_input_list(None)
        raw_inputs = self._pick(inputs_response, ("inputs", "input_list"), []) or []
        for raw in raw_inputs:
            input_name = str(self._pick(raw, ("inputName", "input_name", "sourceName", "source_name"), "")).strip()
            input_kind = str(self._pick(raw, ("inputKind", "input_kind", "sourceType", "source_type"), "")).strip()
            if input_name:
                kinds[input_name] = input_kind
        return kinds

    def _connect(self, initial: bool = False):
        try:
            self.client = ReqClient(
                host=config.obs_host,
                port=config.obs_port,
                password=config.obs_password,
            )
            # Verify connection immediately
            self.client.get_version()
            self.connected = True
            self._last_connect_error = None
            self.logger.info(f"Connected to OBS at {config.obs_host}:{config.obs_port}")

            # Auto-start Replay Buffer if not already running
            # (Fire and forget — don't block connection on this)
            try:
                import asyncio
                if not asyncio.iscoroutinefunction(self._auto_start_replay_buffer):
                    # Call async method synchronously if needed
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(self._auto_start_replay_buffer())
                    loop.close()
            except Exception as e:
                self.logger.debug(f"Auto-start replay buffer error (non-critical): {e}")

            return True
        except Exception as e:
            self.connected = False
            self.client = None
            self._last_connect_error = str(e)
            self._mark_retry_backoff()
            if initial:
                self.logger.warning(f"OBS connection failed: {e}")
                self.logger.warning("OBS WebSocket not available - commands will be logged but not executed")
                self.logger.warning("Start OBS and enable WebSocket server to enable live control")
            return False

    def _ensure_connected(self):
        if self.connected and self.client:
            return True

        if self._now_utc() < self._next_reconnect_at:
            return False

        try:
            self.client = ReqClient(
                host=config.obs_host,
                port=config.obs_port,
                password=config.obs_password,
            )
            self.client.get_version()
            self.connected = True
            self._last_connect_error = None
            self.logger.info(f"Connected to OBS at {config.obs_host}:{config.obs_port}")
            return True
        except Exception as e:
            self.connected = False
            self.client = None
            error_text = str(e)
            if error_text != self._last_connect_error:
                self.logger.warning(f"OBS connection failed: {e}")
                self.logger.warning("OBS WebSocket not available - commands will be logged but not executed")
            self._last_connect_error = error_text
            self._mark_retry_backoff()
            return False

    async def get_stats(self):
        """
        PHASE 3: Real-time Stream Intelligence.
        Returns hardware and stream health metrics.
        """
        if not self._ensure_connected() or not self.client:
            return {"error": "OBS not connected", "mic_muted": False}
        try:
            stream_status = self.client.get_stream_status()
            obs_stats = self.client.get_stats()
            mic_source = os.getenv("OBS_MIC_SOURCE", "Mic/Aux")
            mic_muted = self.get_input_mute(mic_source)

            stream_active = bool(self._extract(stream_status, "output_active", False))
            dropped_frames = int(self._extract(stream_status, "output_skipped_frames", 0) or 0)
            output_bytes = int(self._extract(stream_status, "output_bytes", 0) or 0)
            output_duration_ms = int(self._extract(stream_status, "output_duration", 0) or 0)
            output_congestion = self._safe_float(self._extract(stream_status, "output_congestion", 0.0))
            output_reconnecting = bool(self._extract(stream_status, "output_reconnecting", False))

            # Bitrate estimate:
            # 1) derive from cumulative bytes / duration
            # 2) fallback to delta-bytes sampling when duration is not provided
            bitrate_kbps = 0.0
            if output_bytes > 0 and output_duration_ms > 0:
                seconds = max(output_duration_ms / 1000.0, 0.001)
                bitrate_kbps = (output_bytes * 8.0 / 1000.0) / seconds
            else:
                now = self._now_utc()
                if self._last_stream_bytes is not None and self._last_stream_sample_at is not None:
                    dt = (now - self._last_stream_sample_at).total_seconds()
                    delta = output_bytes - self._last_stream_bytes
                    if dt > 0.25 and delta >= 0:
                        bitrate_kbps = (delta * 8.0 / 1000.0) / dt
                self._last_stream_bytes = output_bytes
                self._last_stream_sample_at = now

            # OBS doesn't expose network latency directly; congestion is the best transport proxy.
            network_latency_ms = int(max(0.0, min(output_congestion, 1.0)) * 120.0)
            fps = round(self._safe_float(self._extract(obs_stats, "active_fps", 0.0)), 1)
            cpu_usage = round(self._safe_float(self._extract(obs_stats, "cpu_usage", 0.0)), 1)
            memory_usage = round(self._safe_float(self._extract(obs_stats, "memory_usage", 0.0)), 1)

            return {
                "active": stream_active,
                "bitrate": round(max(0.0, bitrate_kbps), 1),
                "fps": fps,
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "dropped_frames": dropped_frames,
                "network_latency_ms": network_latency_ms,
                "output_congestion": output_congestion,
                "output_reconnecting": output_reconnecting,
                "mic_muted": bool(mic_muted) if mic_muted is not None else False,
            }
        except Exception as e:
            self._mark_transport_error(e, context="OBS stats unavailable")
            return {"error": "Stats unavailable", "mic_muted": False}

    async def execute(self, action: str, params: dict = None):
        """
        Dispatches actions to specific methods.
        """
        params = params or {}

        actions = {
            "switch_scene": lambda: self.switch_scene(params.get("scene", params.get("scene_name", ""))),
            "mute_mic": lambda: self.mute_mic(),
            "unmute_mic": lambda: self.unmute_mic(),
            "set_audio_level": lambda: self.set_audio_level(
                params.get("source", params.get("input_name", "Mic/Aux")),
                float(params.get("db", params.get("volume_db", -8.0))),
            ),
            "reduce_bitrate": lambda: self.set_stream_bitrate(
                int(params.get("target_kbps", params.get("bitrate_kbps", 4500)) or 4500)
            ),
            "start_recording": self.start_recording,
            "stop_recording": self.stop_recording,
            "start_streaming": self.start_streaming,
            "stop_streaming": self.stop_streaming,
            "toggle_camera": lambda: self.toggle_camera(
                source_name=params.get("source_name") or params.get("source") or "",
                scene_name=params.get("scene_name"),
            ),
            "switch_camera_device": lambda: self.switch_camera_device(
                source_name=params.get("source_name") or params.get("source") or "",
                device_id=params.get("device_id") or params.get("video_device_id") or "",
            ),
            "set_source_visibility": lambda: self.set_source_visibility(
                source_name=params.get("source_name") or params.get("source") or "",
                visible=bool(params.get("visible")),
                scene_name=params.get("scene_name"),
            ),
            "get_available_sources": lambda: self.get_available_sources(
                scene_name=params.get("scene_name"),
            ),
            "get_available_cameras": self.get_available_cameras,
        }

        func = actions.get(action)
        if func:
            return await func()

        self.logger.error(f"Unknown OBS action: {action}")
        return {"status": "error", "reason": f"Unknown action: {action}"}

    async def get_status(self):
        """
        Returns basic connectivity and output state.
        """
        if not self._ensure_connected() or not self.client:
            return {"connected": False, "recording": False, "streaming": False, "current_scene": None, "scenes": []}
        try:
            record_status = self.client.get_record_status()
            stream_status = self.client.get_stream_status()
            res = self.client.get_current_program_scene()
            scene_name = getattr(res, "current_program_scene_name", getattr(res, "scene_name", "Unknown"))
            scenes_response = self.client.get_scene_list()
            scenes = []
            for s in getattr(scenes_response, "scenes", []):
                if isinstance(s, dict):
                    scenes.append(s.get("sceneName") or s.get("name"))
                else:
                    scenes.append(getattr(s, "scene_name", getattr(s, "name", None)))

            return {
                "connected": True,
                "recording": record_status.output_active,
                "streaming": stream_status.output_active,
                "current_scene": scene_name,
                "scenes": [scene for scene in scenes if scene],
            }
        except Exception as e:
            self._mark_transport_error(e, context="OBS status unavailable")
            return {"connected": False, "recording": False, "streaming": False, "current_scene": None, "scenes": []}

    async def switch_scene(self, scene_name: str):
        if not scene_name:
            return {"status": "error", "reason": "No scene name"}
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}

        try:
            scenes_response = self.client.get_scene_list()
            available_scenes = []
            for s in scenes_response.scenes:
                name = None
                if isinstance(s, dict):
                    name = s.get("sceneName") or s.get("name")
                else:
                    name = getattr(s, "scene_name", getattr(s, "name", None))

                if name:
                    available_scenes.append(name)

            target = scene_name.lower().strip()
            match = None

            for s in available_scenes:
                if target == s.lower():
                    match = s
                    break

            if not match:
                for s in available_scenes:
                    if target in s.lower() or s.lower() in target:
                        match = s
                        break

            if match:
                self.client.set_current_program_scene(match)
                self.logger.info(f"Switched to scene: {match}")
                return {"status": "ok", "switched_to": match}

            self.logger.warning(f"Scene '{target}' not found in {available_scenes}")
            return {"status": "error", "message": "Scene not found"}
        except Exception as e:
            self.logger.error(f"OBS switch error: {e}")
            return {"status": "error", "reason": str(e)}

    async def mute_mic(self, input_name: str = "Mic/Aux"):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            self.client.set_input_mute(input_name, True)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def unmute_mic(self, input_name: str = "Mic/Aux"):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            self.client.set_input_mute(input_name, False)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def set_audio_level(self, input_name: str = "Mic/Aux", db: float = -8.0):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            safe_db = max(-60.0, min(20.0, float(db)))
            self.client.set_input_volume(input_name, safe_db, use_decibel=True)
            return {"status": "ok", "source": input_name, "db": safe_db}
        except Exception as e:
            self._mark_transport_error(e, context="OBS audio level change failed")
            return {"status": "error", "reason": str(e)}

    async def set_stream_bitrate(self, target_kbps: int = 4500):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        safe_target = max(1500, min(int(target_kbps or 4500), 12000))
        output_names = ["simple_stream", "adv_stream"]
        bitrate_keys = ("bitrate", "vbitrate", "VBitrate")

        for output_name in output_names:
            try:
                response = self.client.get_output_settings(output_name)
                if isinstance(response, dict):
                    current = response.get("output_settings") or response.get("outputSettings") or {}
                else:
                    current = (
                        getattr(response, "output_settings", None)
                        or getattr(response, "output_settingss", None)
                        or {}
                    )
                if not isinstance(current, dict):
                    continue

                updated = dict(current)
                set_key = None
                for candidate in bitrate_keys:
                    if candidate in updated:
                        set_key = candidate
                        break
                if not set_key:
                    set_key = "bitrate"
                updated[set_key] = safe_target

                self.client.set_output_settings(output_name, updated)
                return {
                    "status": "ok",
                    "bitrate_kbps": safe_target,
                    "output_name": output_name,
                    "key": set_key,
                }
            except Exception:
                continue

        return {"status": "error", "reason": "Could not update OBS output bitrate settings"}

    async def start_recording(self):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            self.client.start_record()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def stop_recording(self):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            self.client.stop_record()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def start_streaming(self):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            self.client.start_stream()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def stop_streaming(self):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            self.client.stop_stream()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def start_replay_buffer(self):
        """Start OBS replay buffer to capture recent footage."""
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            self.client.start_replay_buffer()
            self.logger.info("Replay buffer started")
            return {"status": "ok"}
        except Exception as e:
            self.logger.error(f"Failed to start replay buffer: {e}")
            return {"status": "error", "reason": str(e)}

    async def stop_replay_buffer(self):
        """Stop OBS replay buffer."""
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            self.client.stop_replay_buffer()
            self.logger.info("Replay buffer stopped")
            return {"status": "ok"}
        except Exception as e:
            self.logger.error(f"Failed to stop replay buffer: {e}")
            return {"status": "error", "reason": str(e)}

    async def save_replay_buffer(self):
        """Save current replay buffer content to file."""
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        try:
            self.client.save_replay_buffer()
            self.logger.info("Replay buffer saved")
            return {"status": "ok", "saved": True}
        except Exception as e:
            self.logger.error(f"Failed to save replay buffer: {e}")
            return {"status": "error", "reason": str(e)}

    async def get_replay_buffer_status(self):
        """Get replay buffer status."""
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "active": False}
        try:
            status = self.client.get_replay_buffer_status()
            return {
                "status": "ok",
                "active": status.output_active,
            }
        except Exception as e:
            self._mark_transport_error(e, context="OBS replay buffer status unavailable")
            return {"status": "error", "active": False}

    async def get_all_scene_names(self):
        if not self._ensure_connected() or not self.client:
            return []
        try:
            scenes = self.client.get_scene_list().scenes
            names = []
            for s in scenes:
                if isinstance(s, dict):
                    names.append(s.get("sceneName", s.get("name")))
                else:
                    names.append(getattr(s, "scene_name", getattr(s, "name", None)))
            return [n for n in names if n]
        except Exception:
            return []

    def get_current_scene(self):
        if not self._ensure_connected() or not self.client:
            return "Unknown"
        try:
            response = self.client.get_current_program_scene()
            return getattr(response, "current_program_scene_name", "Unknown")
        except Exception as e:
            self._mark_transport_error(e, context="OBS scene unavailable")
            return "Unknown"

    def set_current_scene(self, scene_name: str):
        if not self._ensure_connected() or not self.client:
            self.logger.warning(f"OBS not connected - cannot switch scene to '{scene_name}'")
            return False
        try:
            self.client.set_current_program_scene(scene_name)
            self.logger.info(f"Switched to scene via direct set: {scene_name}")
            return True
        except Exception as e:
            self._mark_transport_error(e, context="OBS scene switch failed")
            return False

    def set_mute(self, source_name: str, mute_state: bool):
        if not self._ensure_connected() or not self.client:
            self.logger.warning(
                f"OBS not connected - cannot {'mute' if mute_state else 'unmute'} mic '{source_name}'"
            )
            return False

        try:
            self.client.set_input_mute(source_name, mute_state)
            self.logger.info(f"Source '{source_name}' {'muted' if mute_state else 'unmuted'}")
            return True
        except Exception as e:
            self._mark_transport_error(e, context="OBS mute operation failed")
            return False

    def get_input_mute(self, source_name: str) -> bool | None:
        if not self._ensure_connected() or not self.client:
            return None
        try:
            response = self.client.get_input_mute(source_name)
            if isinstance(response, dict):
                raw = response.get("input_muted")
            else:
                raw = getattr(response, "input_muted", None)
            if raw is None:
                return None
            return bool(raw)
        except Exception as e:
            self._mark_transport_error(e, context="OBS input mute check failed")
            return None

    async def get_available_sources(self, scene_name: str | None = None):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected", "sources": []}
        try:
            scene = (scene_name or "").strip() or self._current_scene_name()
            input_kind_by_name = self._input_kind_map()
            response = self.client.get_scene_item_list(scene)
            raw_items = self._pick(response, ("scene_items", "sceneItems"), []) or []

            sources = []
            for raw in raw_items:
                normalized = self._normalize_scene_item(raw, input_kind_by_name=input_kind_by_name)
                if not normalized["source_name"]:
                    continue
                normalized["scene_name"] = scene
                normalized["is_camera"] = self._is_camera_kind(normalized["source_type"])
                sources.append(normalized)

            sources.sort(key=lambda item: item["source_name"].lower())
            return {"status": "ok", "scene_name": scene, "sources": sources}
        except Exception as e:
            self._mark_transport_error(e, context="OBS source list unavailable")
            return {"status": "error", "reason": str(e), "sources": []}

    async def get_available_cameras(self):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected", "cameras": []}
        try:
            system = platform.system().lower()
            if system == "windows":
                preferred_kinds = {"dshow_input"}
            elif system == "darwin":
                preferred_kinds = {"av_capture_input"}
            else:
                preferred_kinds = {"v4l2_input", "dshow_input", "av_capture_input"}

            inputs_response = self.client.get_input_list()
            raw_inputs = self._pick(inputs_response, ("inputs", "input_list"), []) or []

            cameras = []
            for raw in raw_inputs:
                input_name = str(self._pick(raw, ("inputName", "input_name"), "")).strip()
                input_kind = str(self._pick(raw, ("inputKind", "input_kind"), "")).strip()
                input_uuid = str(self._pick(raw, ("inputUuid", "input_uuid"), "")).strip()
                if not input_name or input_kind not in preferred_kinds:
                    continue
                cameras.append(
                    {
                        "device_id": input_uuid or input_name,
                        "label": input_name,
                        "input_kind": input_kind,
                    }
                )

            cameras.sort(key=lambda cam: cam["label"].lower())
            return {"status": "ok", "cameras": cameras}
        except Exception as e:
            self._mark_transport_error(e, context="OBS camera list unavailable")
            return {"status": "error", "reason": str(e), "cameras": []}

    async def _find_scene_source(self, source_name: str, scene_name: str | None = None):
        sources_response = await self.get_available_sources(scene_name=scene_name)
        if sources_response.get("status") != "ok":
            return None, sources_response
        target = (source_name or "").strip().lower()
        scene = sources_response.get("scene_name")
        sources = sources_response.get("sources", [])
        if not target:
            return None, {"status": "error", "reason": "source_name is required", "scene_name": scene, "sources": sources}
        for item in sources:
            if item["source_name"].strip().lower() == target:
                return item, {"status": "ok", "scene_name": scene, "sources": sources}
        return None, {
            "status": "error",
            "reason": f"Source '{source_name}' not found in scene '{scene}'",
            "scene_name": scene,
            "sources": sources,
        }

    async def set_source_visibility(self, source_name: str, visible: bool, scene_name: str | None = None):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        source, context = await self._find_scene_source(source_name=source_name, scene_name=scene_name)
        if not source:
            return context
        try:
            self.client.set_scene_item_enabled(
                context["scene_name"],
                int(source["scene_item_id"]),
                bool(visible),
            )
            return {
                "status": "ok",
                "scene_name": context["scene_name"],
                "source_name": source["source_name"],
                "visible": bool(visible),
                "source_type": source.get("source_type"),
                "is_camera": bool(source.get("is_camera")),
            }
        except Exception as e:
            self._mark_transport_error(e, context="OBS source visibility update failed")
            return {"status": "error", "reason": str(e)}

    async def toggle_camera(self, source_name: str, scene_name: str | None = None):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        source, context = await self._find_scene_source(source_name=source_name, scene_name=scene_name)
        if not source:
            return context
        desired = not bool(source.get("visible"))
        result = await self.set_source_visibility(
            source_name=source["source_name"],
            visible=desired,
            scene_name=context.get("scene_name"),
        )
        if result.get("status") == "ok":
            result["toggled_from"] = bool(source.get("visible"))
        return result

    async def switch_camera_device(self, source_name: str, device_id: str):
        if not self._ensure_connected() or not self.client:
            return {"status": "error", "reason": "OBS not connected"}
        source = (source_name or "").strip()
        device = (device_id or "").strip()
        if not source:
            return {"status": "error", "reason": "source_name is required"}
        if not device:
            return {"status": "error", "reason": "device_id is required"}
        try:
            settings_response = self.client.get_input_settings(source)
            current_settings = self._pick(
                settings_response,
                ("input_settings", "inputSettings", "input_settingss"),
                {},
            ) or {}
            updated_settings = dict(current_settings)
            updated_settings["video_device_id"] = device
            updated_settings["device_id"] = device
            try:
                self.client.set_input_settings(source, updated_settings, True)
            except TypeError:
                self.client.set_input_settings(source, updated_settings)
            return {
                "status": "ok",
                "source_name": source,
                "device_id": device,
            }
        except Exception as e:
            self._mark_transport_error(e, context="OBS camera switch failed")
            return {"status": "error", "reason": str(e)}


# Singleton
obs_bridge = OBSAdapter()

