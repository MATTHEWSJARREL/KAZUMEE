import webbrowser
import asyncio
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
import datetime
from datetime import timezone
import os
import httpx

from .schemas import CommandResult
from backend.core.logger import get_logger
from backend.database.models.platform_connection import PlatformConnection
from backend.core.crypto import decrypt_token


def resolve_clip_requester(payload: Optional[Dict] = None) -> Tuple[str, Optional[object], str]:
    payload = payload or {}

    requester_type = str(payload.get("requester_type") or "").strip().lower() or None
    requester_id = payload.get("requester_id")
    requester_name = payload.get("requester_name") or payload.get("streamer_name") or payload.get("name")

    if requester_type in {"viewer", "streamer", "ai_observer"}:
        if requester_name is None or requester_name == "":
            requester_name = "Anonymous"
        return requester_type, requester_id, str(requester_name)

    role = str(payload.get("role") or payload.get("user_role") or payload.get("requester_role") or "").strip().lower()
    if role == "streamer":
        resolved_name = requester_name or payload.get("streamer_name") or "Anonymous"
        return "streamer", payload.get("streamer_id") or requester_id, str(resolved_name)

    if role == "viewer":
        resolved_name = requester_name or "Anonymous"
        return "viewer", requester_id, str(resolved_name)

    if requester_type is None:
        return "viewer", requester_id, str(requester_name or "Anonymous")

    return requester_type, requester_id, str(requester_name or "Anonymous")


class CommandExecutor:
    def __init__(self, obs=None, clip_searcher=None, broadcaster=None, db_session_factory=None):
        self.log = get_logger("CommandExecutor")
        self.obs = obs
        self.clip_searcher = clip_searcher
        self.broadcaster = broadcaster
        self.db_session_factory = db_session_factory

    # -------------------------------------------------
    # Internal helpers
    # -------------------------------------------------

    def _notify(self, message: str, level: str = "info"):
        if not self.broadcaster:
            return

        try:
            self.broadcaster({
                "type": "notification",
                "data": {
                    "message": message,
                    "level": level,
                },
            })
        except Exception:
            self.log.exception("Failed to send notification")

    async def _exec_obs(self, action: str, params: Dict | None = None):
        if not self.obs:
            return {"status": "skipped", "reason": "OBS adapter not configured"}

        return await self.obs.execute(action, params or {})

    async def _get_obs_status(self):
        if not self.obs:
            return {
                "connected": False,
                "recording": False,
                "streaming": False,
            }
        try:
            # obs.get_status() is async, so we must await it.
            return await self.obs.get_status()
        except TypeError:
            # Backward-compatible fallback if adapter returns sync method.
            self.log.warning("OBS Adapter returned synchronous status, fixing...")
            if asyncio.iscoroutinefunction(self.obs.get_status):
                return await self.obs.get_status()
            return self.obs.get_status()
        except Exception:
            self.log.exception("Failed to fetch OBS status")
            return {
                "connected": False,
                "recording": False,
                "streaming": False,
            }

    # -------------------------------------------------
    # Camera name resolution
    # -------------------------------------------------

    def _resolve_camera_friendly_name(self, streamer_id: int, friendly_name: str) -> Optional[Tuple[str, str]]:
        """
        Resolve friendly camera name (e.g., 'facecam') to OBS source name and device ID.
        Returns tuple of (obs_source_name, obs_device_id) or None if not found.
        """
        if not self.db_session_factory or not streamer_id or not friendly_name:
            return None
        
        db = self.db_session_factory()
        try:
            from backend.database.models.streamer_camera_source import StreamerCameraSource
            
            mapping = (
                db.query(StreamerCameraSource)
                .filter(
                    StreamerCameraSource.streamer_id == streamer_id,
                    StreamerCameraSource.friendly_name.ilike(friendly_name),  # Case-insensitive
                )
                .first()
            )
            
            if not mapping:
                self.log.warning(f"Camera mapping not found for '{friendly_name}' (streamer {streamer_id})")
                return None
            
            obs_source = str(mapping.obs_source_name or "").strip()
            obs_device = str(mapping.obs_device_id or "").strip()
            
            if not obs_source or not obs_device:
                self.log.warning(f"Camera mapping incomplete for '{friendly_name}': source={obs_source}, device={obs_device}")
                return None
            
            self.log.info(f"Resolved camera '{friendly_name}' -> source={obs_source}, device={obs_device}")
            return (obs_source, obs_device)
        
        except Exception as e:
            self.log.error(f"Camera mapping lookup failed: {e}")
            return None
        finally:
            db.close()

    # -------------------------------------------------
    # Platform integrations (Twitch)
    # -------------------------------------------------

    def _get_twitch_connection(self, streamer_id: int):
        if not self.db_session_factory or not streamer_id:
            return None
        db = self.db_session_factory()
        try:
            conn = (
                db.query(PlatformConnection)
                .filter(
                    PlatformConnection.streamer_id == streamer_id,
                    PlatformConnection.platform == "twitch",
                )
                .first()
            )
            if not conn:
                return None
            meta = conn.meta or {}
            return {
                "access_token": decrypt_token(conn.access_token) if conn.access_token else None,
                "broadcaster_id": str(meta.get("broadcaster_id") or ""),
                "moderator_id": str(meta.get("moderator_id") or meta.get("broadcaster_id") or ""),
            }
        finally:
            db.close()

    async def _twitch_resolve_user_id(self, *, access_token: str, username: str) -> str | None:
        client_id = os.getenv("TWITCH_CLIENT_ID", "")
        if not client_id or not access_token or not username:
            return None

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": client_id,
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                "https://api.twitch.tv/helix/users",
                params={"login": username},
                headers=headers,
            )
        if res.status_code >= 300:
            return None
        data = res.json().get("data") or []
        if not data:
            return None
        return str(data[0].get("id") or "")

    async def _apply_twitch_chat_shield(
        self,
        *,
        streamer_id: int,
        follower_only_minutes: int,
        slow_mode_seconds: int,
    ) -> dict:
        conn = self._get_twitch_connection(streamer_id)
        if not conn or not conn.get("access_token"):
            return {"status": "error", "reason": "Twitch not connected for this streamer"}

        broadcaster_id = conn.get("broadcaster_id") or ""
        moderator_id = conn.get("moderator_id") or ""
        if not broadcaster_id or not moderator_id:
            return {"status": "error", "reason": "Missing broadcaster_id/moderator_id in Twitch metadata"}

        headers = {
            "Authorization": f"Bearer {conn['access_token']}",
            "Client-Id": os.getenv("TWITCH_CLIENT_ID", ""),
            "Content-Type": "application/json",
        }
        body = {
            "follower_mode": True,
            "follower_mode_duration": max(0, int(follower_only_minutes)),
            "slow_mode": True,
            "slow_mode_wait_time": max(3, int(slow_mode_seconds)),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.patch(
                "https://api.twitch.tv/helix/chat/settings",
                params={
                    "broadcaster_id": broadcaster_id,
                    "moderator_id": moderator_id,
                },
                headers=headers,
                json=body,
            )
        if res.status_code >= 300:
            return {"status": "error", "reason": f"Twitch chat shield failed: {res.text}"}
        return {"status": "ok", "provider": "twitch", "settings": body}

    async def _apply_twitch_moderation_action(
        self,
        *,
        streamer_id: int,
        action: str,
        username: str | None = None,
        user_id: str | None = None,
        duration_seconds: int = 600,
        reason: str = "Kazumi moderation action",
    ) -> dict:
        conn = self._get_twitch_connection(streamer_id)
        if not conn or not conn.get("access_token"):
            return {"status": "error", "reason": "Twitch not connected for this streamer"}

        broadcaster_id = conn.get("broadcaster_id") or ""
        moderator_id = conn.get("moderator_id") or ""
        access_token = conn.get("access_token") or ""
        if not broadcaster_id or not moderator_id:
            return {"status": "error", "reason": "Missing broadcaster_id/moderator_id in Twitch metadata"}

        target_user_id = (user_id or "").strip()
        if not target_user_id and username:
            target_user_id = await self._twitch_resolve_user_id(
                access_token=access_token,
                username=username.strip().lower(),
            ) or ""
        if not target_user_id:
            return {"status": "error", "reason": "Unable to resolve target user for moderation action"}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": os.getenv("TWITCH_CLIENT_ID", ""),
            "Content-Type": "application/json",
        }

        if action not in {"timeout", "ban"}:
            return {"status": "ok", "provider": "twitch", "message": f"No hard enforcement for action '{action}'"}

        ban_payload = {"user_id": target_user_id, "reason": reason[:500]}
        if action == "timeout":
            ban_payload["duration"] = max(1, min(int(duration_seconds), 1_209_600))

        body = {"data": ban_payload}
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                "https://api.twitch.tv/helix/moderation/bans",
                params={
                    "broadcaster_id": broadcaster_id,
                    "moderator_id": moderator_id,
                },
                headers=headers,
                json=body,
            )
        if res.status_code >= 300:
            return {"status": "error", "reason": f"Twitch moderation failed: {res.text}"}
        return {
            "status": "ok",
            "provider": "twitch",
            "action": action,
            "target_user_id": target_user_id,
            "username": username,
        }

    async def _create_twitch_clip(self, *, streamer_id: int, has_delay: bool = True) -> dict:
        conn = self._get_twitch_connection(streamer_id)
        if not conn or not conn.get("access_token"):
            return {"status": "error", "reason": "Twitch not connected for this streamer"}

        broadcaster_id = conn.get("broadcaster_id") or ""
        if not broadcaster_id:
            return {"status": "error", "reason": "Missing broadcaster_id in Twitch metadata"}

        headers = {
            "Authorization": f"Bearer {conn['access_token']}",
            "Client-Id": os.getenv("TWITCH_CLIENT_ID", ""),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                "https://api.twitch.tv/helix/clips",
                params={
                    "broadcaster_id": broadcaster_id,
                    "has_delay": str(bool(has_delay)).lower(),
                },
                headers=headers,
            )
        if res.status_code >= 300:
            return {"status": "error", "reason": f"Twitch clip create failed: {res.text}"}
        body = res.json()
        item = (body.get("data") or [{}])[0]
        return {
            "status": "ok",
            "provider": "twitch",
            "clip_id": item.get("id"),
            "edit_url": item.get("edit_url"),
        }

    async def _validate_obs_truth(self, command: str) -> bool:
        # This will now be a proper Dictionary, not a Coroutine
        status = await self._get_obs_status()

        if command == "start_recording":
            return status.get("recording") is True

        if command == "stop_recording":
            return status.get("recording") is False

        if command == "start_streaming":
            return status.get("streaming") is True

        if command == "stop_streaming":
            return status.get("streaming") is False

        return True

    # -------------------------------------------------
    # Command execution
    # -------------------------------------------------

    async def execute(self, command: str, payload: Dict, streamer_id: Optional[int] = None) -> CommandResult:
        self.log.info("Executing command=%s payload=%s", command, payload)
        
        # Import audio feedback
        from backend.core.audio_feedback import play_command_feedback
        from backend.core.activity_logger import log_command_executed
        
        # Extract streamer_id from payload if not provided as parameter
        if not streamer_id:
            streamer_id = payload.get("streamer_id")

        # Helper to log command execution after success
        async def _log_command_success(cmd: str, msg: str, meta: dict = None):
            if streamer_id and self.db_session_factory:
                db = None
                try:
                    db = self.db_session_factory()
                    await log_command_executed(
                        db=db,
                        streamer_id=streamer_id,
                        command=cmd,
                        status="success",
                        result_message=msg,
                        metadata=meta,
                    )
                except Exception as e:
                    self.log.debug(f"Activity logging failed: {e}")
                finally:
                    if db:
                        db.close()

        # Helper to log command execution on error
        async def _log_command_error(cmd: str, msg: str):
            if streamer_id and self.db_session_factory:
                db = None
                try:
                    db = self.db_session_factory()
                    await log_command_executed(
                        db=db,
                        streamer_id=streamer_id,
                        command=cmd,
                        status="error",
                        result_message=msg,
                    )
                except Exception as e:
                    self.log.debug(f"Activity logging failed: {e}")
                finally:
                    if db:
                        db.close()

        # ---------------- OBS COMMANDS ----------------

        if command == "start_recording":
            await self._exec_obs("start_recording")
            await asyncio.sleep(0.8)

            success = await self._validate_obs_truth("start_recording")
            status = await self._get_obs_status()

            self._notify(
                "Recording started" if success else "Recording failed",
                "success" if success else "error",
            )
            
            # Play audio feedback on success
            if success:
                try:
                    await play_command_feedback("start_recording")
                except Exception as e:
                    self.log.debug(f"Audio feedback failed: {e}")
                
                # Log to activity feed
                await _log_command_success("start_recording", "Recording started")

            return CommandResult(
                status="ok" if success else "error",
                message="Recording started" if success else "Recording failed",
                data={"obs": status},
            )

        if command == "stop_recording":
            await self._exec_obs("stop_recording")
            await asyncio.sleep(0.8)

            success = await self._validate_obs_truth("stop_recording")
            status = await self._get_obs_status()

            self._notify(
                "Recording stopped" if success else "Recording still active",
                "success" if success else "error",
            )
            
            # Play audio feedback on success
            if success:
                try:
                    await play_command_feedback("stop_recording")
                except Exception as e:
                    self.log.debug(f"Audio feedback failed: {e}")
                
                # Log to activity feed
                await _log_command_success("stop_recording", "Recording stopped")

            return CommandResult(
                status="ok" if success else "error",
                message="Recording stopped" if success else "Recording still active",
                data={"obs": status},
            )

        if command == "start_streaming":
            await self._exec_obs("start_streaming")
            await asyncio.sleep(0.8)

            success = await self._validate_obs_truth("start_streaming")
            status = await self._get_obs_status()

            self._notify(
                "Stream started" if success else "Stream failed to start",
                "success" if success else "error",
            )
            
            # Play audio feedback on success
            if success:
                try:
                    await play_command_feedback("start_streaming")
                except Exception as e:
                    self.log.debug(f"Audio feedback failed: {e}")
                
                # Log to activity feed
                await _log_command_success("start_streaming", "Stream started")

            return CommandResult(
                status="ok" if success else "error",
                message="Stream started" if success else "Stream failed",
                data={"obs": status},
            )

        if command == "stop_streaming":
            await self._exec_obs("stop_streaming")
            await asyncio.sleep(0.8)

            success = await self._validate_obs_truth("stop_streaming")
            status = await self._get_obs_status()

            self._notify(
                "Stream stopped" if success else "Stream still active",
                "success" if success else "error",
            )
            
            # Play audio feedback on success
            if success:
                try:
                    await play_command_feedback("stop_streaming")
                except Exception as e:
                    self.log.debug(f"Audio feedback failed: {e}")
                
                # Log to activity feed
                await _log_command_success("stop_streaming", "Stream stopped")

            return CommandResult(
                status="ok" if success else "error",
                message="Stream stopped" if success else "Stream still active",
                data={"obs": status},
            )

        if command == "switch_scene":
            scene = payload.get("scene")
            if not scene:
                return CommandResult(status="error", message="No scene provided")

            result = await self._exec_obs("switch_scene", {"scene": scene})
            if result.get("status") != "ok":
                return CommandResult(status="error", message=result.get("reason", "Scene switch failed"))

            await asyncio.sleep(0.2)

            status = await self._get_obs_status()

            self._notify(f"Switched to scene: {scene}", "info")
            
            # Play audio feedback
            try:
                await play_command_feedback("switch_scene")
            except Exception as e:
                self.log.debug(f"Audio feedback failed: {e}")
            
            # Log to activity feed
            await _log_command_success("switch_scene", f"Switched to scene: {scene}", {"scene": scene})

            return CommandResult(
                status="ok",
                message=f"Scene switched to {scene}",
                data={"obs": status, "scene": scene},
            )

        if command == "mute_mic":
            result = await self._exec_obs("mute_mic")
            if result.get("status") != "ok":
                return CommandResult(status="error", message="Failed to mute microphone")

            self._notify("Microphone muted", "info")
            
            # Play audio feedback
            try:
                await play_command_feedback("mute_mic")
            except Exception as e:
                self.log.debug(f"Audio feedback failed: {e}")
            
            # Log to activity feed
            await _log_command_success("mute_mic", "Microphone muted")

            return CommandResult(
                status="ok",
                message="Microphone muted",
            )

        if command == "unmute_mic":
            result = await self._exec_obs("unmute_mic")
            if result.get("status") != "ok":
                return CommandResult(status="error", message="Failed to unmute microphone")

            self._notify("Microphone unmuted", "info")
            
            # Play audio feedback
            try:
                await play_command_feedback("unmute_mic")
            except Exception as e:
                self.log.debug(f"Audio feedback failed: {e}")
            
            # Log to activity feed
            await _log_command_success("unmute_mic", "Microphone unmuted")

            return CommandResult(
                status="ok",
                message="Microphone unmuted",
            )

        if command == "set_audio_level":
            source = payload.get("source", payload.get("input_name", "Mic/Aux"))
            db_level = payload.get("db", payload.get("volume_db", -8.0))
            result = await self._exec_obs(
                "set_audio_level",
                {"source": source, "db": db_level},
            )
            if result.get("status") != "ok":
                return CommandResult(
                    status="error",
                    message=result.get("reason", "Failed to set audio level"),
                )
            self._notify(
                f"Audio level set: {source} -> {result.get('db')} dB",
                "info",
            )
            return CommandResult(
                status="ok",
                message=f"Set {source} to {result.get('db')} dB",
                data=result,
            )

        if command == "reduce_bitrate":
            target_kbps = int(payload.get("target_kbps", payload.get("bitrate_kbps", 4500)) or 4500)
            result = await self._exec_obs(
                "reduce_bitrate",
                {"target_kbps": target_kbps},
            )
            if result.get("status") != "ok":
                return CommandResult(
                    status="error",
                    message=result.get("reason", "Failed to adjust stream bitrate"),
                    data=result,
                )
            self._notify(f"Stream Doctor applied bitrate {result.get('bitrate_kbps')} kbps", "warning")
            return CommandResult(
                status="ok",
                message=f"Bitrate adjusted to {result.get('bitrate_kbps')} kbps",
                data=result,
            )

        if command == "toggle_camera":
            source_name = str(payload.get("source_name") or payload.get("source") or "").strip()
            if not source_name:
                return CommandResult(status="error", message="source_name is required")
            result = await self._exec_obs(
                "toggle_camera",
                {
                    "source_name": source_name,
                    "scene_name": payload.get("scene_name"),
                },
            )
            if result.get("status") != "ok":
                return CommandResult(status="error", message=result.get("reason", "Could not toggle camera"), data=result)
            visibility_label = "visible" if result.get("visible") else "hidden"
            self._notify(f"{source_name} is now {visibility_label}", "info")
            
            # Play audio feedback
            try:
                await play_command_feedback("toggle_camera")
            except Exception as e:
                self.log.debug(f"Audio feedback failed: {e}")
            
            # Log to activity feed
            await _log_command_success("toggle_camera", f"{source_name} is now {visibility_label}", {"source": source_name, "visible": result.get("visible")})
            
            return CommandResult(
                status="ok",
                message=f"{source_name} is now {visibility_label}",
                data=result,
            )

        if command == "switch_camera_device":
            # Get source and device from payload
            source_name_or_alias = str(payload.get("source_name") or payload.get("source") or "").strip()
            device_id = str(payload.get("device_id") or payload.get("video_device_id") or "").strip()
            streamer_id_param = payload.get("streamer_id")
            
            # If device_id is missing, try to resolve friendly name from StreamerCameraSource
            if streamer_id_param and not device_id:
                mapping = self._resolve_camera_friendly_name(streamer_id_param, source_name_or_alias)
                if mapping:
                    source_name_or_alias, device_id = mapping
                    self.log.info(f"Resolved camera alias '{payload.get('source_name')}' to source='{source_name_or_alias}', device='{device_id}'")
            
            if not source_name_or_alias:
                return CommandResult(status="error", message="source_name is required")
            if not device_id:
                return CommandResult(status="error", message="device_id is required - could not resolve camera mapping")
            
            result = await self._exec_obs(
                "switch_camera_device",
                {
                    "source_name": source_name_or_alias,
                    "device_id": device_id,
                },
            )
            if result.get("status") != "ok":
                return CommandResult(status="error", message=result.get("reason", "Could not switch camera device"), data=result)
            self._notify(f"Camera source {source_name_or_alias} switched", "info")
            
            # Play audio feedback
            try:
                await play_command_feedback("switch_camera_device")
            except Exception as e:
                self.log.debug(f"Audio feedback failed: {e}")
            
            # Log to activity feed
            await _log_command_success("switch_camera_device", f"Camera source {source_name_or_alias} switched", {"source": source_name_or_alias, "device_id": device_id})
            
            return CommandResult(
                status="ok",
                message=f"Camera source {source_name_or_alias} switched",
                data=result,
            )

        if command == "set_source_visibility":
            source_name = str(payload.get("source_name") or payload.get("source") or "").strip()
            if not source_name:
                return CommandResult(status="error", message="source_name is required")
            if "visible" not in payload:
                return CommandResult(status="error", message="visible is required")
            result = await self._exec_obs(
                "set_source_visibility",
                {
                    "source_name": source_name,
                    "visible": bool(payload.get("visible")),
                    "scene_name": payload.get("scene_name"),
                },
            )
            if result.get("status") != "ok":
                return CommandResult(status="error", message=result.get("reason", "Could not change source visibility"), data=result)
            visibility_label = "visible" if result.get("visible") else "hidden"
            self._notify(f"{source_name} set to {visibility_label}", "info")
            
            # Play audio feedback
            try:
                await play_command_feedback("set_source_visibility")
            except Exception as e:
                self.log.debug(f"Audio feedback failed: {e}")
            
            # Log to activity feed
            await _log_command_success("set_source_visibility", f"{source_name} set to {visibility_label}", {"source": source_name, "visible": result.get("visible")})
            
            return CommandResult(
                status="ok",
                message=f"{source_name} set to {visibility_label}",
                data=result,
            )

        if command == "get_available_sources":
            result = await self._exec_obs(
                "get_available_sources",
                {"scene_name": payload.get("scene_name")},
            )
            if result.get("status") != "ok":
                return CommandResult(status="error", message=result.get("reason", "Could not list sources"), data=result)
            scene_name = result.get("scene_name") or "current scene"
            return CommandResult(
                status="ok",
                message=f"Listed sources for {scene_name}",
                data=result,
            )

        if command == "get_available_cameras":
            result = await self._exec_obs("get_available_cameras")
            if result.get("status") != "ok":
                return CommandResult(status="error", message=result.get("reason", "Could not list cameras"), data=result)
            count = len(result.get("cameras", []))
            return CommandResult(
                status="ok",
                message=f"Found {count} camera device{'s' if count != 1 else ''}",
                data=result,
            )

        # ---------------- NON-OBS COMMANDS ----------------

        if command == "open_dashboard":
            try:
                webbrowser.open("http://localhost:5173")
                self._notify("Dashboard opened", "success")
                return CommandResult(status="ok", message="Dashboard opened")
            except Exception:
                self.log.exception("Failed to open dashboard")
                self._notify("Failed to open dashboard", "error")
                return CommandResult(status="error", message="Failed to open dashboard")

        if command == "report_status":
            status = await self._get_obs_status()
            return CommandResult(
                status="ok",
                message="Current system status",
                data={"obs": status},
            )

        if command == "create_clip":
            # Improved clip creation with naming and timestamps
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            clip_name = f"clip_{timestamp}"

            if self.clip_searcher:
                try:
                    # Trigger clip creation logic (placeholder for now)
                    # In future, this could integrate with actual clip detection/recording
                    self._notify(f"Clip '{clip_name}' created", "success")
                    
                    # Play audio feedback for clip creation
                    try:
                        await play_command_feedback("create_clip")
                    except Exception as e:
                        self.log.debug(f"Audio feedback failed: {e}")
                    
                    # Log to activity feed
                    await _log_command_success("create_clip", f"Clip '{clip_name}' created", {"clip": clip_name, "timestamp": timestamp})
                    
                    return CommandResult(
                        status="ok",
                        message=f"Clip '{clip_name}' created",
                        data={"clip": clip_name, "timestamp": timestamp},
                    )
                except Exception:
                    self.log.exception("Clip creation failed")
                    return CommandResult(status="error", message="Failed to create clip")
            else:
                return CommandResult(status="error", message="Clip searcher not available")

        if command == "search_clip":
            query = payload.get("query", "")
            results = []

            if self.clip_searcher:
                try:
                    results = self.clip_searcher.search_multi(query, limit=5)
                except Exception:
                    self.log.exception("Clip search failed")

            if self.broadcaster:
                try:
                    self.broadcaster({
                        "type": "search_results",
                        "data": {
                            "query": query,
                            "results": results,
                        },
                    })
                except Exception:
                    self.log.exception("Failed to broadcast search results")

            return CommandResult(
                status="ok",
                message="Search completed",
                data={"results": results},
            )

        if command == "chat":
            if self.broadcaster:
                try:
                    self.broadcaster({
                        "type": "chat_response",
                        "data": {"message": payload.get("message", "")},
                    })
                except Exception:
                    self.log.exception("Chat broadcast failed")

            return CommandResult(status="ok", message="Chat message sent")

        if command == "panic_mode":
            # PANIC MODE: Emergency safety sequence
            # 1. Switch to BRB/Technical Difficulties scene
            # 2. Mute microphone
            # 3. Mute desktop audio

            panic_scene = payload.get("panic_scene", "BRB")  # Default to BRB scene

            # Execute panic sequence
            scene_result = await self._exec_obs("switch_scene", {"scene": panic_scene})
            mic_result = self.obs.set_mute("Mic/Aux", True)

            # Try to mute desktop audio (common source names)
            desktop_sources = ["Desktop Audio", "Audio Output Capture", "Wasapi Output Capture"]
            desktop_muted = False
            for source in desktop_sources:
                try:
                    self.obs.client.set_input_mute(source, True)
                    desktop_muted = True
                    break
                except:
                    continue

            # Check results
            scene_ok = scene_result.get("status") == "ok"
            mic_ok = mic_result

            if scene_ok and mic_ok:
                self._notify("🛡️ SHIELD ACTIVE - Emergency mode engaged", "warning")
                return CommandResult(
                    status="ok",
                    message="Emergency mode activated - Scene switched, audio muted",
                    data={
                        "panic_scene": panic_scene,
                        "mic_muted": True,
                        "desktop_muted": desktop_muted
                    },
                )
            else:
                self._notify("⚠️ Emergency mode partially failed", "error")
                return CommandResult(
                    status="error",
                    message="Emergency mode failed - check OBS connection",
                    data={
                        "scene_switched": scene_ok,
                        "mic_muted": mic_ok,
                        "desktop_muted": desktop_muted
                    },
                )

        if command == "save_replay_buffer":
            # SAVE REPLAY BUFFER: Create a clip record for review
            try:
                # Get database session
                db = self.db_session_factory()

                # Create clip record
                from backend.database.models.clip import Clip
                from backend.database.models.stream_session import StreamSession
                from backend.database.models.streamer import Streamer
                from backend.core.event_store import insert_stream_event
                from backend.core.taste import extract_tags_from_text, score_clip
                import datetime

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                clip_filename = f"replay_buffer_{timestamp}.mp4"
                clip_path = os.path.join("backend", "data", "clips", clip_filename)

                # Get requester info from payload
                requester_type, requester_id, requester_name = resolve_clip_requester(payload)

                session = db.query(StreamSession).filter(StreamSession.id == 1).first()
                streamer_id = session.streamer_id if session else None
                streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first() if streamer_id else None
                tags = extract_tags_from_text(f"{requester_name} {clip_filename}")
                quality_score = score_clip(streamer.taste_profile if streamer else None, tags)

                clip = Clip(
                    file_path=clip_path,
                    requested_by_type=requester_type,
                    requested_by_id=requester_id,
                    requested_by_name=requester_name,
                    title=f"Clip requested by {requester_name}",
                    description=f"Replay buffer clip from {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    stream_session_id=1,  # Default session
                    streamer_id=streamer_id,
                    tags=tags,
                    quality_score=quality_score,
                    status="pending" if requester_type == "viewer" else "approved",
                    is_public=requester_type != "viewer"
                )

                db.add(clip)
                db.commit()
                db.refresh(clip)

                # Auto-export for high-confidence / AI observer
                auto_export = payload.get("auto_export") is True
                if auto_export or requester_type == "ai_observer":
                    from backend.core.export import queue_short_form_export
                    job = queue_short_form_export(
                        db,
                        clip_id=clip.id,
                        streamer_id=streamer_id,
                        input_path=clip.file_path,
                        preset="tiktok",
                        watermark_text=payload.get("watermark_text") or requester_name,
                        subtitles_path=payload.get("subtitles_path"),
                    )
                    clip.export_status = "queued"
                    clip.export_preset = job.get("preset")
                    clip.export_path = job.get("output_path")
                    clip.export_updated_at = datetime.datetime.now(timezone.utc)
                    db.commit()

                if streamer_id:
                    insert_stream_event(
                        db,
                        streamer_id=streamer_id,
                        platform="kazumi_ai",
                        event_type="clip_created",
                        event_id=f"clip_created:{clip.id}",
                        user_id=str(requester_id or ""),
                        username=requester_name,
                        message=f"Clip saved: {clip.title or f'Clip #{clip.id}'}",
                        payload={
                            "clip_id": clip.id,
                            "status": clip.status,
                            "title": clip.title,
                            "url": clip.file_path,
                            "thumbnail_url": clip.thumbnail_path,
                            "moment_label": (clip.tags[0] if isinstance(clip.tags, list) and clip.tags else None),
                        },
                    )
                    if requester_type == "viewer":
                        insert_stream_event(
                            db,
                            streamer_id=streamer_id,
                            platform="viewer",
                            event_type="viewer_clip_ready",
                            event_id=f"viewer_clip_ready:{clip.id}",
                            user_id=str(requester_id or ""),
                            username=requester_name,
                            message=f"Viewer clip ready: {clip.title or f'Clip #{clip.id}'}",
                            payload={
                                "clip_id": clip.id,
                                "status": clip.status,
                                "title": clip.title,
                                "url": clip.file_path,
                                "thumbnail_url": clip.thumbnail_path,
                                "moment_label": (clip.tags[0] if isinstance(clip.tags, list) and clip.tags else None),
                            },
                        )
                    db.commit()

                # Broadcast clip creation event
                if self.broadcaster:
                    try:
                        self.broadcaster({
                            "type": "CLIP_SAVED",
                            "data": {
                                "clip_id": clip.id,
                                "requester_type": requester_type,
                                "requester_name": requester_name,
                                "status": clip.status
                            }
                        })
                    except Exception:
                        self.log.exception("Failed to broadcast clip saved event")

                self._notify(f"Clip saved for review (ID: {clip.id})", "success")
                return CommandResult(
                    status="ok",
                    message=f"Clip saved successfully. {'Pending approval.' if requester_type == 'viewer' else 'Approved automatically.'}",
                    data={"clip_id": clip.id, "status": clip.status}
                )

            except Exception as e:
                self.log.exception("Failed to save replay buffer clip")
                return CommandResult(status="error", message="Failed to save clip")

        if command == "notify":
            # System notification action
            message = payload.get("message", "System notification")
            level = payload.get("level", "info")
            self._notify(message, level)
            return CommandResult(status="ok", message="Notification sent")

        if command == "crosspost_hype_update":
            teaser = payload.get("teaser") or "Insane moment happening right now. Join live."
            webhook_url = payload.get("discord_webhook_url") or os.getenv("DISCORD_WEBHOOK_URL", "")
            posted = False
            if webhook_url:
                try:
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        res = await client.post(webhook_url, json={"content": teaser})
                    posted = res.status_code < 300
                except Exception:
                    posted = False
            self._notify(f"Crosspost queued: {teaser}", "info")
            return CommandResult(
                status="ok",
                message="Cross-platform hype update queued",
                data={"teaser": teaser, "discord_posted": posted},
            )

        if command == "create_twitch_clip":
            streamer_id = int(payload.get("streamer_id") or 0)
            result = (
                await self._create_twitch_clip(
                    streamer_id=streamer_id,
                    has_delay=bool(payload.get("has_delay", True)),
                )
                if streamer_id
                else {"status": "error", "reason": "streamer_id is required"}
            )
            return CommandResult(
                status="ok" if result.get("status") == "ok" else "error",
                message="Twitch clip created" if result.get("status") == "ok" else "Twitch clip creation failed",
                data=result,
            )

        if command == "lock_chat_follower_only":
            streamer_id = int(payload.get("streamer_id") or 0)
            follower_only_minutes = int(payload.get("follower_only_minutes", 10) or 10)
            slow_mode_seconds = int(payload.get("slow_mode_seconds", 5) or 5)
            result = (
                await self._apply_twitch_chat_shield(
                    streamer_id=streamer_id,
                    follower_only_minutes=follower_only_minutes,
                    slow_mode_seconds=slow_mode_seconds,
                )
                if streamer_id
                else {"status": "error", "reason": "streamer_id is required"}
            )
            if result.get("status") == "ok":
                self._notify("Shield mode activated on Twitch chat settings", "warning")
            else:
                self._notify(f"Shield mode fallback (not enforced): {result.get('reason', 'unknown')}", "warning")
            return CommandResult(
                status="ok" if result.get("status") == "ok" else "error",
                message="Chat shield action enforced" if result.get("status") == "ok" else "Chat shield action failed",
                data=result,
            )

        if command == "moderation_auto_action":
            action = str(payload.get("action", "timeout") or "timeout").lower()
            target = payload.get("username", "unknown_user")
            streamer_id = int(payload.get("streamer_id") or 0)
            result = (
                await self._apply_twitch_moderation_action(
                    streamer_id=streamer_id,
                    action=action,
                    username=str(target),
                    user_id=payload.get("user_id"),
                    duration_seconds=int(payload.get("duration_seconds", 600) or 600),
                    reason=payload.get("reason", "Kazumi moderation action"),
                )
                if streamer_id
                else {"status": "error", "reason": "streamer_id is required"}
            )
            if result.get("status") == "ok":
                self._notify(f"Moderation enforced: {action} -> {target}", "warning")
            else:
                self._notify(f"Moderation enforcement failed: {result.get('reason', 'unknown')}", "error")
            return CommandResult(
                status="ok" if result.get("status") == "ok" else "error",
                message="Moderation action enforced" if result.get("status") == "ok" else "Moderation action failed",
                data={"action": action, "username": target, "result": result},
            )

        # ---------------- FALLBACK ----------------

        return CommandResult(status="error", message="Unknown command")


