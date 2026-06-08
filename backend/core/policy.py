from typing import Dict, Optional

from backend.database.session import SessionLocal
from backend.database.models.streamer import Streamer


DEFAULT_POLICY: Dict[str, str] = {
    # viewer automatic
    "chat": "allow",
    "ask_lore": "allow",
    "request_clip": "allow",
    "vote_scene": "allow",
    "suggestion": "allow",

    # needs approval
    "switch_scene": "approve",
    "mute_mic": "approve",
    "unmute_mic": "approve",
    "start_recording": "approve",
    "stop_recording": "approve",
    "toggle_camera": "approve",
    "switch_camera_device": "approve",
    "set_source_visibility": "approve",
    "reduce_bitrate": "approve",

    # streamer only
    "start_streaming": "deny",
    "stop_streaming": "deny",
    "panic_mode": "deny",
    "restart_engine": "deny",
}


def get_policy_for_streamer(streamer_id: Optional[int]) -> Dict[str, str]:
    if not streamer_id:
        return dict(DEFAULT_POLICY)
    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        overrides = streamer.policy_json if streamer and streamer.policy_json else {}
        return {**DEFAULT_POLICY, **overrides}
    finally:
        db.close()


def evaluate_action(action: str, role: str, streamer_id: Optional[int] = None) -> str:
    """
    Returns: allow | approve | deny
    """
    if role == "streamer":
        return "allow"
    policy = get_policy_for_streamer(streamer_id)
    return policy.get(action, "approve")
