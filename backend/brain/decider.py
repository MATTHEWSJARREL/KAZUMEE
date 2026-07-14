import logging
from typing import List
from .schemas import BrainDecision, BrainAction
from backend.brain.scene_aliases import SCENE_ALIASES

logger = logging.getLogger(__name__)

class BrainDecider:
    def __init__(self):
        logger.info("BrainDecider initialized")

    def decide(self, command: str, live_scenes: List[str]) -> BrainDecision:
        text = command.lower().strip()
        text_tokens = set(text.split())

        def infer_source_name(raw_text: str) -> str:
            if any(token in raw_text for token in ("facecam", "webcam", "camera")):
                return "Webcam"
            if "overlay" in raw_text:
                return "Overlay"
            if "brb" in raw_text:
                return "BRB"
            return "Webcam"

        # 0. SOURCE/CAMERA CONTROL
        if any(token in text for token in ("facecam", "webcam", "camera", "overlay")):
            source_name = infer_source_name(text)
            if any(token in text for token in ("hide", "off", "disable")):
                return BrainDecision(
                    "set_source_visibility",
                    "execute",
                    BrainAction.SET_SOURCE_VISIBILITY,
                    f"Hiding {source_name}",
                    0.9,
                    {"source_name": source_name, "visible": False},
                )
            if any(token in text for token in ("show", "on", "enable")):
                return BrainDecision(
                    "set_source_visibility",
                    "execute",
                    BrainAction.SET_SOURCE_VISIBILITY,
                    f"Showing {source_name}",
                    0.9,
                    {"source_name": source_name, "visible": True},
                )
            if "toggle" in text:
                return BrainDecision(
                    "toggle_camera",
                    "execute",
                    BrainAction.TOGGLE_CAMERA,
                    f"Toggling {source_name}",
                    0.9,
                    {"source_name": source_name},
                )
            if any(token in text for token in ("switch", "change")) and "camera" in text:
                device_id = "camera_2_device_id" if any(token in text for token in ("2", "two", "second")) else "camera_1_device_id"
                return BrainDecision(
                    "switch_camera_device",
                    "execute",
                    BrainAction.SWITCH_CAMERA_DEVICE,
                    f"Switching {source_name} device",
                    0.85,
                    {"source_name": source_name, "device_id": device_id},
                )
            if any(token in text for token in ("list", "available", "connected")):
                if "camera" in text:
                    return BrainDecision(
                        "get_available_cameras",
                        "execute",
                        BrainAction.GET_AVAILABLE_CAMERAS,
                        "Listing connected camera devices",
                        0.85,
                        {},
                    )
                return BrainDecision(
                    "get_available_sources",
                    "execute",
                    BrainAction.GET_AVAILABLE_SOURCES,
                    "Listing current scene sources",
                    0.85,
                    {},
                )

        # 1. SCENE SWITCHING
        if any(k in text for k in ("switch", "go to", "change")):
            best_match, best_score = None, 0
            for scene in live_scenes:
                scene_tokens = set(scene.lower().split())
                score = len(scene_tokens & text_tokens)
                for alias_scene, aliases in SCENE_ALIASES.items():
                    if alias_scene.lower() == scene.lower():
                        score = max(score, len(set(aliases) & text_tokens))
                if score > best_score:
                    best_score, best_match = score, scene

            if best_match:
                return BrainDecision("switch_scene", "execute", BrainAction.SWITCH_SCENE, f"Switching to {best_match}", 0.9, {"scene": best_match})

        # 2. RECORDING
        if "record" in text:
            if "start" in text:
                return BrainDecision("start_rec", "execute", BrainAction.START_RECORDING, "Starting", 1.0)
            if "stop" in text:
                return BrainDecision("stop_rec", "execute", BrainAction.STOP_RECORDING, "Stopping", 1.0)

        # 3. MIC
        if "mic" in text or "mute" in text or "audio" in text:
            if "unmute" in text or "unmute mic" in text:
                return BrainDecision("unmute", "execute", BrainAction.UNMUTE_MIC, "Unmuting mic", 1.0)
            if "mute" in text or any(token in text for token in ("mute mic", "silence mic", "kill audio")):
                return BrainDecision("mute", "execute", BrainAction.MUTE_MIC, "Muting mic", 1.0)
            # Handle toggle for mic/audio
            if "toggle" in text or "switch" in text or "change" in text:
                # If user says "change mic" or "toggle mic", assume they want to toggle
                if any(token in text for token in ("mic", "mute", "audio")):
                    return BrainDecision("toggle_mic", "execute", BrainAction.MUTE_MIC, "Toggling mic state", 0.85)

        # 4. SEARCH/WEB LOOKUP
        if any(phrase in text for phrase in ["pull", "search", "find", "grab", "get me", "show me"]):
            if not any(phrase in text for phrase in ["pull chat", "search chat", "pull stream"]):  # Avoid false positives
                # Extract the search query (everything after the action word)
                query = text
                for trigger in ["pull", "search", "find", "grab", "get me", "show me"]:
                    if trigger in text:
                        query = text.split(trigger, 1)[-1].strip()
                        break
                return BrainDecision("search", "execute", BrainAction.SEARCH_CLIP, f"Searching for: {query}", 0.85, {"query": query})

        # 5. CLIPPING
        if any(phrase in text for phrase in ["clip that", "save that", "capture that"]):
            return BrainDecision("clip", "execute", BrainAction.SAVE_REPLAY_BUFFER, "Saving clip", 0.95)

        # 6. PANIC/SAFETY MODE
        if any(phrase in text for phrase in ["shields up", "panic", "tos", "emergency"]):
            return BrainDecision("panic", "execute", BrainAction.PANIC_MODE, "Emergency mode activated", 1.0)

        return BrainDecision("unknown", "refuse", None, "Command not recognized", 0.0)

brain_decider = BrainDecider()
