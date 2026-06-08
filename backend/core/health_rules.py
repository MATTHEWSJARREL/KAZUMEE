from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List


@dataclass
class HealthAction:
    key: str
    action: str
    confidence: float
    reason: str
    severity: str
    execute: bool = False
    payload: dict | None = None


_last_action: Dict[str, datetime] = {}


def _recommended_bitrate(current_bitrate: float) -> int:
    baseline = current_bitrate if current_bitrate and current_bitrate > 0 else 6000
    return int(max(2500, min(6000, baseline - 1000)))


def _cooldown_ok(key: str, seconds: int) -> bool:
    now = datetime.utcnow()
    last = _last_action.get(key)
    if last and (now - last).total_seconds() < seconds:
        return False
    _last_action[key] = now
    return True


def evaluate_health(metrics: dict) -> List[HealthAction]:
    actions: List[HealthAction] = []

    cpu = float(metrics.get("cpu", 0))
    mem = float(metrics.get("mem", 0))
    latency = float(metrics.get("latency_ms", 0))
    current_bitrate = float(metrics.get("bitrate_kbps", 0) or 0)
    auto_apply = bool(metrics.get("auto_apply", False))
    obs_connected = bool(metrics.get("obs_connected", True))

    if cpu > 85:
        rec_bitrate = _recommended_bitrate(current_bitrate)
        should_execute = auto_apply and obs_connected and cpu >= 92
        actions.append(
            HealthAction(
                key="cpu_high",
                action="reduce_bitrate",
                confidence=0.82 if cpu < 95 else 0.9,
                reason=f"CPU usage {cpu:.0f}% is high. Suggested bitrate: {rec_bitrate} kbps.",
                severity="warning",
                execute=should_execute,
                payload={"target_kbps": rec_bitrate},
            )
        )

    if mem > 85:
        actions.append(
            HealthAction(
                key="mem_high",
                action="close_background_apps",
                confidence=0.78 if mem < 95 else 0.88,
                reason=f"Memory usage {mem:.0f}% is high.",
                severity="warning",
                execute=False,
            )
        )

    if latency > 80:
        rec_bitrate = _recommended_bitrate(current_bitrate)
        should_execute = auto_apply and obs_connected and latency >= 120
        actions.append(
            HealthAction(
                key="latency_high",
                action="reduce_bitrate",
                confidence=0.76,
                reason=f"Network latency {latency:.0f}ms is elevated. Suggested bitrate: {rec_bitrate} kbps.",
                severity="warning",
                execute=should_execute,
                payload={"target_kbps": rec_bitrate},
            )
        )

    if not obs_connected:
        actions.append(
            HealthAction(
                key="obs_offline",
                action="notify",
                confidence=0.95,
                reason="OBS connection lost. Reconnect needed.",
                severity="high",
                execute=True,
                payload={"message": "OBS disconnected. Please reconnect.", "level": "error"},
            )
        )

    if cpu > 95 or mem > 95:
        actions.append(
            HealthAction(
                key="critical_resource",
                action="notify",
                confidence=0.92,
                reason="System under heavy load. Streamer-selected scene will stay active.",
                severity="high",
                execute=True,
                payload={
                    "message": "System under heavy load. Scene unchanged.",
                    "level": "warning",
                },
            )
        )

    return actions


def filter_actions(actions: List[HealthAction], *, cooldown_sec: int = 120) -> List[HealthAction]:
    filtered = []
    for action in actions:
        key = f"{action.key}:{action.action}"
        if _cooldown_ok(key, cooldown_sec):
            filtered.append(action)
    return filtered
