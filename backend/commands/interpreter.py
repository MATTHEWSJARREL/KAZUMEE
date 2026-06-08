# LEGACY — DO NOT USE FOR BRAIN PATH
# BrainDecider is the authoritative decision engine.
# This file is kept for potential fallback or legacy routes only.

from typing import Tuple, Dict, Optional

class CommandInterpreter:
    def interpret(self, text: str) -> Tuple[Optional[str], Dict]:
        # 1. Clean the input text
        t = text.lower().strip()

        # --- RECORDING COMMANDS ---
        # Matches: "start recording", "start record", "begin recording", "record"
        if any(x in t for x in ["start recording", "start record", "begin recording"]) or t == "record":
            return "start_recording", {}
        
        # Matches: "stop recording", "stop record", "end recording", "finish recording"
        if any(x in t for x in ["stop recording", "stop record", "end recording", "finish recording"]):
            return "stop_recording", {}

        # --- STREAMING COMMANDS ---
        if "start streaming" in t or "start stream" in t or "go live" in t:
            return "start_streaming", {}
        
        if "stop streaming" in t or "stop stream" in t or "end stream" in t:
            return "stop_streaming", {}

        # --- UI COMMANDS ---
        if "open" in t and "dashboard" in t:
            return "open_dashboard", {}

        # --- SCENE SWITCHING ---
        # Matches: "switch to scene: Gameplay", "switch to Gameplay", "scene: Gameplay"
        if "switch to" in t or t.startswith("scene:"):
            # Clean up the string to get just the scene name
            scene_name = t.replace("switch to", "").replace("scene:", "").strip()
            return "switch_scene", {"scene": scene_name}

        # --- SOURCE / CAMERA CONTROL ---
        if any(phrase in t for phrase in ["hide facecam", "hide webcam", "show facecam", "show webcam"]):
            visible = not ("hide" in t)
            return "set_source_visibility", {"source_name": "Webcam", "visible": visible}

        if "toggle" in t and any(word in t for word in ["camera", "webcam", "facecam"]):
            return "toggle_camera", {"source_name": "Webcam"}

        if ("switch" in t or "change" in t) and "camera" in t:
            # Map second/two/2 to symbolic device ID for real-device resolution
            device_id = "camera_2" if any(token in t for token in ["2", "two", "second"]) else "camera_1"
            return "switch_camera_device", {"source_name": "Webcam", "device_id": device_id}

        if "sources" in t and any(phrase in t for phrase in ["available", "list", "show"]):
            return "get_available_sources", {}

        if "camera" in t and any(phrase in t for phrase in ["available", "connected", "list", "show"]):
            return "get_available_cameras", {}

        # --- CLIP SEARCHING ---
        # Matches: "find clip of a headshot", "search clip headshot"
        clip_triggers = ["find clip", "search clip", "look for clip"]
        if any(trigger in t for trigger in clip_triggers):
            query = t
            for trigger in clip_triggers:
                query = query.replace(trigger, "")
            return "search_clip", {"query": query.strip()}

        # --- CHAT COMMANDS ---
        # Matches: "chat: hello everyone", "say in chat hello"
        if t.startswith("chat:"):
            return "chat", {"message": t.replace("chat:", "").strip()}
        
        if "say in chat" in t:
            return "chat", {"message": t.replace("say in chat", "").strip()}

        # 2. Fallback if no keywords matched
        return None, {}
