from typing import Dict, List, Optional
import re


def _normalize_tags(tags) -> List[str]:
    if not tags:
        return []
    if isinstance(tags, list):
        return [str(t).lower().strip() for t in tags if str(t).strip()]
    return []


PRESET_PROFILES: Dict[str, Dict] = {
    "rager": {
        "scoring_weights": {"velocity": 0.6, "keywords": 0.25, "intensity": 0.15},
        "keyword_boosts": {"rage": 0.3, "insane": 0.25, "clip": 0.2, "wtf": 0.2, "pog": 0.15},
        "scene_weights": {"gameplay": 0.9, "reaction": 0.7, "brb": 0.1},
        "clip_length": {"min": 8, "max": 40, "ideal": 18, "weight": 0.12},
        "description": "High energy, fast clips, chat spikes.",
    },
    "pro": {
        "scoring_weights": {"velocity": 0.45, "keywords": 0.35, "intensity": 0.2},
        "keyword_boosts": {"clutch": 0.3, "win": 0.25, "headshot": 0.2, "comeback": 0.2},
        "scene_weights": {"gameplay": 1.0, "reaction": 0.4, "brb": 0.1},
        "clip_length": {"min": 12, "max": 55, "ideal": 28, "weight": 0.15},
        "description": "Competitive plays, clutch moments, longer context.",
    },
    "cozy": {
        "scoring_weights": {"velocity": 0.35, "keywords": 0.45, "intensity": 0.2},
        "keyword_boosts": {"aww": 0.25, "lore": 0.2, "chat": 0.2, "cute": 0.2},
        "scene_weights": {"gameplay": 0.5, "reaction": 0.8, "brb": 0.2},
        "clip_length": {"min": 15, "max": 75, "ideal": 35, "weight": 0.1},
        "description": "Community moments, lore, softer pacing.",
    },
}


def _default_profile() -> Dict:
    return {
        "preset": "balanced",
        "scoring_weights": {"velocity": 0.5, "keywords": 0.35, "intensity": 0.15},
        "keyword_boosts": {},
        "scene_weights": {},
        "clip_length": {"min": 10, "max": 60, "ideal": 25, "weight": 0.1},
        "tags": {},
        "approved": 0,
        "rejected": 0,
        "last_tags": [],
    }


def apply_preset(profile: Optional[Dict], preset: str) -> Dict:
    base = _default_profile()
    preset_data = PRESET_PROFILES.get(preset, {})
    merged = {**base, **preset_data}
    merged["preset"] = preset if preset in PRESET_PROFILES else "balanced"
    if profile:
        merged["tags"] = profile.get("tags", merged["tags"])
        merged["approved"] = profile.get("approved", merged["approved"])
        merged["rejected"] = profile.get("rejected", merged["rejected"])
    return merged


def _adjust_weight(value: float, delta: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
    return max(min(value + delta, max_val), min_val)


def update_taste_profile(
    profile: Dict,
    tags: List[str],
    approved: bool,
    *,
    duration_seconds: Optional[float] = None,
) -> Dict:
    profile = profile or _default_profile()
    tag_counts = profile.get("tags") or {}
    keyword_boosts = profile.get("keyword_boosts") or {}
    approved_count = int(profile.get("approved") or 0)
    rejected_count = int(profile.get("rejected") or 0)

    for tag in tags:
        current = int(tag_counts.get(tag) or 0)
        tag_counts[tag] = current + (1 if approved else -1)
        current_boost = float(keyword_boosts.get(tag) or 0.0)
        keyword_boosts[tag] = _adjust_weight(current_boost, 0.05 if approved else -0.03)

    if duration_seconds is not None:
        clip_pref = profile.get("clip_length") or _default_profile().get("clip_length")
        ideal = float(clip_pref.get("ideal") or 25)
        if approved:
            ideal = (ideal * 0.8) + (duration_seconds * 0.2)
        else:
            ideal = (ideal * 0.9) + (duration_seconds * 0.1)
        clip_pref["ideal"] = round(ideal, 1)
        profile["clip_length"] = clip_pref

    if approved:
        approved_count += 1
    else:
        rejected_count += 1

    profile.update(
        {
            "tags": tag_counts,
            "keyword_boosts": keyword_boosts,
            "approved": approved_count,
            "rejected": rejected_count,
            "last_tags": tags,
        }
    )
    return profile


def score_clip(profile: Dict, tags: List[str], duration_seconds: Optional[float] = None) -> float:
    profile = profile or _default_profile()
    tag_counts = profile.get("tags") or {}
    keyword_boosts = profile.get("keyword_boosts") or {}
    score = 0.5
    for tag in tags:
        weight = tag_counts.get(tag, 0)
        score += min(max(weight / 10.0, -0.2), 0.2)
        score += min(max(float(keyword_boosts.get(tag, 0.0)), -0.1), 0.1)

    if duration_seconds is not None:
        clip_pref = profile.get("clip_length") or {}
        ideal = float(clip_pref.get("ideal") or 25)
        weight = float(clip_pref.get("weight") or 0.1)
        distance = abs(duration_seconds - ideal) / max(ideal, 1)
        score -= min(distance * weight, 0.2)

    return round(max(min(score, 1.0), 0.0), 3)


def extract_tags(clip_tags) -> List[str]:
    return _normalize_tags(clip_tags)


def extract_tags_from_text(text: str) -> List[str]:
    if not text:
        return []
    text = text.lower()
    keywords = [
        "clutch",
        "funny",
        "rage",
        "insane",
        "epic",
        "fail",
        "headshot",
        "win",
        "loss",
        "reaction",
        "speedrun",
        "comeback",
        "highlight",
        "clip",
    ]
    found = []
    for key in keywords:
        if re.search(rf"\b{re.escape(key)}\b", text):
            found.append(key)
    return found
