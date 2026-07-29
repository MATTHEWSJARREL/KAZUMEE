import asyncio
import os
import sys
import json
from typing import Optional
from groq import Groq
from backend.core.logger import get_logger
from .interpreter import CommandInterpreter
from .executor import CommandExecutor
from .schemas import CommandRequest, CommandResult


class CommandService:
    def __init__(self, executor: Optional[CommandExecutor] = None):
        self.log = get_logger("CommandService")
        self.interpreter = CommandInterpreter()
        self.executor = executor or CommandExecutor()
        self._canonical_commands = {
            "switch_scene",
            "start_recording",
            "stop_recording",
            "start_streaming",
            "stop_streaming",
            "mute_mic",
            "unmute_mic",
            "set_audio_level",
            "reduce_bitrate",
            "toggle_camera",
            "switch_camera_device",
            "set_source_visibility",
            "get_available_sources",
            "get_available_cameras",
            "open_dashboard",
            "report_status",
            "create_clip",
            "search_clip",
            "chat",
            "panic_mode",
            "save_replay_buffer",
            "auto_clip",
            "create_twitch_clip",
            "crosspost_hype_update",
            "lock_chat_follower_only",
            "moderation_auto_action",
        }
        
        # Phase 1: Initialize Groq Client (optional for V1 MVP)
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if api_key:
            self.ai_client = Groq(api_key=api_key)
        else:
            self.log.warning("GROQ_API_KEY not set - AI commands will be limited")
            self.ai_client = None

    async def handle(self, request: CommandRequest):
        try:
            raw_text = request.text.strip() if request.text else ""
            self.log.info(f"Processing command: '{raw_text}' | Brain: {request.is_brain}")

            # --- PATH A: SYSTEM EVENTS (Recursive) ---
            if request.is_brain and raw_text.startswith("system:"):
                system_event = raw_text.replace("system:", "")
                return await self._process_with_ai(system_event, is_event=True)

            # --- PATH B: BRAIN INPUT (AI Processing) ---
            if request.is_brain:
                return await self._process_with_ai(raw_text, is_event=False)

            # --- PATH C: LEGACY/CANONICAL PATH (Direct Execution) ---
            else:
                if request.is_canonical or raw_text in self._canonical_commands:
                    canonical = raw_text
                    derived = {}
                else:
                    canonical, derived = self.interpreter.interpret(raw_text)

                if not canonical:
                    self.log.warning(f"No match for: '{raw_text}'")
                    return CommandResult(status="error", message=f"Unknown command: {raw_text}")

                payload = (request.metadata or {}).copy()
                payload.update(derived)

                self.log.info(f"Executing: {canonical} with {payload}")
                result = await asyncio.wait_for(
                    self.executor.execute(canonical, payload),
                    timeout=5.0,
                )
                return result

        except asyncio.TimeoutError:
            self.log.error(f"Timeout on: {raw_text}")
            return CommandResult(status="timeout", message="OBS is lagging - check connection")
        except Exception as e:
            self.log.exception("Internal service failure")
            return CommandResult(status="error", message=str(e))

    async def _process_with_ai(self, text: str, is_event: bool = False):
        """
        Phase 1 & 2: Uses Groq to determine intent and commentary.
        """
        # 1. Gather Live Context for the AI (optional - only if OBS available)
        scenes = []
        status = {}
        obs_stats = {}
        sources = []
        cameras = []
        
        if self.executor.obs:
            try:
                scenes = await self.executor.obs.get_all_scene_names()
                status = await self.executor.obs.get_status()
                obs_stats = await self.executor.obs.get_stats()
                available_sources_payload = await self.executor.obs.get_available_sources()
                sources = [
                    src.get("source_name")
                    for src in (available_sources_payload or {}).get("sources", [])
                    if src.get("source_name")
                ][:24]
                cameras_payload = await self.executor.obs.get_available_cameras()
                cameras = [
                    {"device_id": cam.get("device_id"), "label": cam.get("label")}
                    for cam in (cameras_payload or {}).get("cameras", [])
                ][:16]
            except Exception as e:
                self.log.warning(f"Failed to gather OBS context: {e}")
                # Continue with empty values - OBS-dependent actions will fail later if needed

        # 2. Construct Groq intent translation prompt (more robust casual speech)
        current_scene = status.get("current_scene") if status else "Unknown"

        # OBS stats/mic state/viewer count may not exist in all deployments; pass safe fallbacks.
        mic_muted = None
        is_streaming = None
        viewer_count = None

        if status:
            # common keys used by various adapters
            mic_muted = status.get("mic_muted")
            if mic_muted is None:
                mic_muted = status.get("mic_status")
            is_streaming = status.get("is_streaming")
            if is_streaming is None:
                is_streaming = status.get("streaming")

        if obs_stats:
            viewer_count = obs_stats.get("viewer_count") or obs_stats.get("viewers")

        speech = text

        pythonZUMI_COMMAND_PROMPT = """
You are Zumi, a live stream control assistant.
Your ONLY job is to translate what the streamer says into stream control commands.
You do NOT answer questions. You do NOT search the web. You do NOT give advice.
You ONLY return a JSON command object.

Current stream state:
- Scene: {current_scene}
- Streaming: {is_streaming}
- Mic muted: {mic_muted}
- Viewer count: {viewer_count}

The streamer said: "{speech}"

Translate this into ONE of these exact commands:

switch_scene - change OBS scene
clip_now - save replay buffer as clip
search_clip - search web for clip/link via keywords
mute_mic - mute microphone
unmute_mic - unmute microphone
start_recording - start OBS recording
stop_recording - stop OBS recording
start_stream - go live
stop_stream - end stream
set_source_visibility - show or hide a source
set_audio_level - change volume
go_brb - switch to BRB scene
ignore - streamer is talking to chat, not to Zumi

Rules:
- "clip that" / "save that" / "get that" / "Zumi clip it" = clip_now
- "pull the [thing]" / "search for [thing]" / "find me [thing]" / "grab that [thing]" = search_clip
- "go BRB" / "I need a break" / "be right back" = go_brb
- "mute" / "kill the mic" / "silence" = mute_mic
- "unmute" / "mic on" = unmute_mic
- "switch to [name]" / "go to [name]" / "change to [name]" = switch_scene
- If unclear or confidence below 0.5 = ignore

Return ONLY this JSON, nothing else, no explanation, no markdown:
{{"intent": "command_name", "params": {{}}, "confidence": 0.0}}

Examples:
Input: "clip that"
Output: {{"intent": "clip_now", "params": {{}}, "confidence": 0.95}}

Input: "pull the tiktok of the guy who does backflips over lambos"
Output: {{"intent": "search_clip", "params": {{"query": "backflips over lambos tiktok"}}, "confidence": 0.88}}

Input: "switch to my face cam"
Output: {{"intent": "switch_scene", "params": {{"scene": "facecam"}}, "confidence": 0.90}}

Input: "yo go BRB real quick"
Output: {{"intent": "go_brb", "params": {{}}, "confidence": 0.92}}

Input: "chat what do you guys think"
Output: {{"intent": "ignore", "params": {{}}, "confidence": 0.95}}
"""

        prompt = pythonZUMI_COMMAND_PROMPT.format(
            current_scene=current_scene,
            is_streaming=is_streaming,
            mic_muted=mic_muted,
            viewer_count=viewer_count,
            speech=speech,
        )


        try:
            # 3. Call Groq
            completion = self.ai_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are Zumi. Output ONLY valid JSON as instructed by the user prompt."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            decision = json.loads(completion.choices[0].message.content)
            self.log.info(f"AI Decision: {decision}")

            # 4. Execute Decision based on new Zumi schema (intent/confidence/params/response)
            exec_result = None

            intent = decision.get("intent")
            confidence = decision.get("confidence")
            params = decision.get("params") or {}
            response_text = decision.get("response")

            obs_required_intents = {
                "switch_scene",
                "mute_mic",
                "unmute_mic",
                "set_source_visibility",
                "set_audio_level",
                "start_recording",
                "stop_recording",
                "start_stream",
                "stop_stream",
                "go_brb",
            }

            if intent in obs_required_intents and not self.executor.obs:
                return CommandResult(
                    status="error",
                    message="OBS adapter unavailable for this action.",
                    data={"intent": intent}
                )

            # unclear: no action, just return to caller
            if intent == "unclear":
                return CommandResult(
                    status="partial",
                    message="unclear",
                    data={
                        "intent": intent,
                        "confidence": confidence,
                        "params": params,
                        "response": response_text,
                    },
                    intent=intent,
                )

            # ignore: viewer talking to chat, no action
            if intent == "ignore":
                return CommandResult(
                    status="success",
                    message="ignored",
                    data={
                        "intent": intent,
                        "confidence": confidence,
                        "params": params,
                    },
                    intent=intent,
                )

            # answer: just surface response
            if intent == "answer":
                return CommandResult(
                    status="success",
                    message=response_text or "",
                    data={
                        "intent": intent,
                        "confidence": confidence,
                        "params": params,
                        "response": response_text,
                    },
                    intent=intent,
                )

            # action intents: dispatch canonical command
            if intent in {
                "switch_scene",
                "mute_mic",
                "unmute_mic",
                "set_source_visibility",
                "set_audio_level",
                "start_recording",
                "stop_recording",
                "start_stream",
                "stop_stream",
                "go_brb",
                "clip_now",
                "search_clip",
            }:
                # Map Zumi intents to your canonical command names
                canonical = {
                    "switch_scene": "switch_scene",
                    "mute_mic": "mute_mic",
                    "unmute_mic": "unmute_mic",
                    "set_source_visibility": "set_source_visibility",
                    "set_audio_level": "set_audio_level",
                    "start_recording": "start_recording",
                    "stop_recording": "stop_recording",
                    "start_stream": "start_streaming",
                    "stop_stream": "stop_streaming",
                    "go_brb": "switch_scene",
                    "clip_now": "save_replay_buffer",
                    "search_clip": "search_clip",
                }.get(intent)
                if intent == "go_brb":
                    params = {**params, "scene": params.get("scene") or "BRB"}

                if canonical:
                    cmd = CommandRequest(
                        text=canonical,
                        metadata=params,
                        is_canonical=True,
                    )
                    exec_result = await self.handle(cmd)

            # 5. Return for Frontend Consumption as CommandResult
            result_status = "success"
            if isinstance(exec_result, CommandResult):
                result_status = exec_result.status
            elif isinstance(exec_result, dict) and "status" in exec_result:
                result_status = exec_result.get("status", "success")

            return CommandResult(
                status=result_status,
                message=response_text or "Command processed.",
                data={
                    "intent": intent,
                    "confidence": confidence,
                    "params": params,
                    "response": response_text,
                    "result": exec_result.dict() if isinstance(exec_result, CommandResult) else exec_result,
                },
                intent=intent,
            )


        except Exception as e:
            self.log.error(f"Groq processing failed: {e}")
            return CommandResult(status="error", message="Brain link severed.")

