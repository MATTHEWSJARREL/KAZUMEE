"""Tier entitlement checks for feature gating."""
from __future__ import annotations

_TIER_ORDER = ("free", "creator", "pro")
_FEATURES = {
    "unlimited_clips": "creator",
    "ai_moderation": "creator", 
    "voice_agent": "creator",
    "backseat_gaming": "creator",
    "full_viewer_companion": "pro",
    "historical_context": "pro",
    "clip_export": "creator",
    "streamer_ai": "creator",
}
_VIEWER_FEATURES = {
    "ask_zumi",
    "catchup_companion",
    "chat_cleanse",
    "clip_export",
    "full_viewer_companion",
    "historical_context",
    "viewer_actions",
    "viewer_basics",
    "viewer_clip_request",
    "vibe_matcher",
}


def is_viewer_feature(feature_name: str) -> bool:
    """Return True when a feature is part of the public viewer experience."""
    return (feature_name or "").strip().lower() in _VIEWER_FEATURES

def _idx(tier: str) -> int:
    t = (tier or "free").strip().lower()
    try:
        return _TIER_ORDER.index(t)
    except ValueError:
        return 0

def check_tier_feature(current_tier: str, feature: str):
    """Returns (allowed, minimum_tier). minimum_tier is None when allowed."""
    if is_viewer_feature(feature):
        return True, None
    min_tier = _FEATURES.get(feature, "creator")
    ok = _idx(current_tier) >= _idx(min_tier)
    return ok, None if ok else min_tier

class TierFeatureError(ValueError):
    def __init__(self, feature: str, current_tier: str, minimum_tier: str):
        self.feature = feature
        self.current_tier = current_tier
        self.minimum_tier = minimum_tier
        message = f"Feature '{feature}' requires {minimum_tier} tier (you have {current_tier})"
        super().__init__(message)

    def to_api_response(self) -> dict:
        return {
            "error": "insufficient_tier",
            "feature": self.feature,
            "current_tier": self.current_tier,
            "minimum_tier": self.minimum_tier,
            "message": f"Upgrade to {self.minimum_tier} to unlock '{self.feature}'. Subscribe at /pricing",
        }

def require_feature(user_tier: str, feature: str) -> None:
    ok, min_tier = check_tier_feature(user_tier, feature)
    if not ok:
        raise TierFeatureError(feature=feature, current_tier=user_tier, minimum_tier=min_tier)
