# backend/core/brain/state.py

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class SystemState:
    """
    Canonical snapshot of system truth at decision time.
    """
    obs_connected: bool
    recording: bool
    streaming: bool
    scene: Optional[str] = None

    # NEW: Enriched state for smarter decisions
    available_scenes: Optional[List[str]] = None
    recording_duration: Optional[float] = None
    stream_uptime: Optional[float] = None
