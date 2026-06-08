# backend/core/brain/schemas.py

from dataclasses import dataclass
from typing import Optional, Dict, Literal
from enum import Enum


# ----------------------------
# BRAIN ACTIONS (LOCKED CONTRACT)
# ----------------------------

class BrainAction(Enum):
    START_RECORDING = "start_recording"
    STOP_RECORDING = "stop_recording"
    START_STREAMING = "start_streaming"
    STOP_STREAMING = "stop_streaming"
    SWITCH_SCENE = "switch_scene"
    MUTE_MIC = "mute_mic"
    UNMUTE_MIC = "unmute_mic"
    TOGGLE_CAMERA = "toggle_camera"
    SWITCH_CAMERA_DEVICE = "switch_camera_device"
    SET_SOURCE_VISIBILITY = "set_source_visibility"
    GET_AVAILABLE_SOURCES = "get_available_sources"
    GET_AVAILABLE_CAMERAS = "get_available_cameras"
    START_REPLAY_BUFFER = "start_replay_buffer"
    STOP_REPLAY_BUFFER = "stop_replay_buffer"
    SAVE_REPLAY_BUFFER = "save_replay_buffer"
    OPEN_DASHBOARD = "open_dashboard"
    REPORT_STATUS = "report_status"
    CREATE_CLIP = "create_clip"
    SEARCH_CLIP = "search_clip"
    CHAT = "chat"
    NOTIFY = "notify"
    PANIC_MODE = "panic_mode"


# ----------------------------
# INPUT TO THE BRAIN
# ----------------------------

@dataclass
class BrainInput:
    """
    Normalized input passed into the brain.
    NOTHING else should decide intent outside this structure.
    """
    source: Literal["voice", "text", "system"]
    raw_text: str
    metadata: Dict


# ----------------------------
# WORLD STATE (READ-ONLY)
# ----------------------------

@dataclass
class BrainContext:
    """
    Snapshot of the world as seen by the brain.
    This is injected — the brain never fetches data itself.
    """
    obs_connected: bool
    recording: bool
    streaming: bool
    scene: Optional[str]


# ----------------------------
# BRAIN OUTPUT
# ----------------------------

@dataclass
class BrainDecision:
    """
    Final, authoritative decision made by the brain.
    """
    intent: str                     # e.g. "start_recording"
    decision: Literal[
        "execute",
        "refuse",
        "defer"
    ]
    action: Optional[BrainAction]    # executor command name (locked to enum)
    reason: str                     # human-readable explanation
    confidence: float               # 0.0 – 1.0
    payload: Optional[Dict] = None  # additional data for action
