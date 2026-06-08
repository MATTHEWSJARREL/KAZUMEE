from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from datetime import datetime, timedelta
from typing import Deque
import os


HYPE_KEYWORDS = {
    "pog", "poggers", "omg", "lol", "lmao", "wtf", "clip it", "clipit", "insane",
    "holy", "wow", "nuts", "crazy", "gg", "sheesh", "lets go", "let's go",
}


@dataclass
class ScoringRules:
    window_seconds: int = 15
    velocity_weight: float = 0.5
    keyword_weight: float = 0.35
    intensity_weight: float = 0.15
    velocity_peak_mps: float = 2.0  # messages per second for 100 score
    keyword_peak: int = 6  # keyword hits in window for 100 score
    high_threshold: float = 75.0
    medium_threshold: float = 50.0
    keyword_boosts: dict[str, float] | None = None


def rules_from_profile(profile: dict | None) -> ScoringRules:
    profile = profile or {}
    weights = profile.get("scoring_weights") or {}
    keyword_boosts = profile.get("keyword_boosts") or {}
    return ScoringRules(
        velocity_weight=float(weights.get("velocity", 0.5)),
        keyword_weight=float(weights.get("keywords", 0.35)),
        intensity_weight=float(weights.get("intensity", 0.15)),
        keyword_boosts=keyword_boosts,
    )


class Hypemeter:
    def __init__(self, rules: ScoringRules | None = None):
        self.rules = rules or ScoringRules()
        self._timestamps: Deque[datetime] = deque()
        self._messages: Deque[str] = deque()

    def _trim(self, now: datetime):
        cutoff = now - timedelta(seconds=self.rules.window_seconds)
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
            if self._messages:
                self._messages.popleft()

    def add_message(self, message: str, ts: datetime | None = None) -> None:
        now = ts or datetime.utcnow()
        self._timestamps.append(now)
        self._messages.append(message or "")
        self._trim(now)

    def _velocity_score(self) -> float:
        count = len(self._timestamps)
        mps = count / max(self.rules.window_seconds, 1)
        return min(100.0, (mps / max(self.rules.velocity_peak_mps, 0.1)) * 100.0)

    def _keyword_score(self) -> float:
        hits = 0
        boosts = self.rules.keyword_boosts or {}
        dynamic_keywords = set(HYPE_KEYWORDS) | set(boosts.keys())
        for msg in self._messages:
            lower = msg.lower()
            for kw in dynamic_keywords:
                if kw in lower:
                    hits += 1 + float(boosts.get(kw, 0.0))
                    break
            # caps ratio boost
            letters = [c for c in msg if c.isalpha()]
            if letters:
                caps = sum(1 for c in letters if c.isupper())
                if caps / max(len(letters), 1) >= 0.6 and len(letters) >= 8:
                    hits += 1
        return min(100.0, (hits / max(self.rules.keyword_peak, 1)) * 100.0)

    def _intensity_score(self, intensity: float | None) -> float:
        if intensity is None:
            return 0.0
        return max(0.0, min(100.0, intensity))

    def score(self, intensity: float | None = None) -> dict:
        velocity = self._velocity_score()
        keywords = self._keyword_score()
        intensity_score = self._intensity_score(intensity)

        total = (
            velocity * self.rules.velocity_weight
            + keywords * self.rules.keyword_weight
            + intensity_score * self.rules.intensity_weight
        )

        if total >= self.rules.high_threshold:
            confidence = "high"
        elif total >= self.rules.medium_threshold:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "score": round(total, 1),
            "confidence": confidence,
            "signals": {
                "velocity": round(velocity, 1),
                "keywords": round(keywords, 1),
                "intensity": round(intensity_score, 1),
            },
        }


_meters: dict[int, Hypemeter] = {}
_last_trigger: dict[int, datetime] = {}


def get_meter(streamer_id: int, rules: ScoringRules | None = None) -> Hypemeter:
    if streamer_id not in _meters:
        _meters[streamer_id] = Hypemeter(rules)
    elif rules is not None:
        _meters[streamer_id].rules = rules
    return _meters[streamer_id]


def can_trigger(streamer_id: int) -> bool:
    cooldown = int(os.getenv("AUTO_CLIP_COOLDOWN_SEC", "90"))
    last = _last_trigger.get(streamer_id)
    now = datetime.utcnow()
    if last and (now - last).total_seconds() < cooldown:
        return False
    _last_trigger[streamer_id] = now
    return True
