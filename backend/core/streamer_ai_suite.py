from __future__ import annotations

from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
import re
from typing import Any


DEFAULT_STREAMER_AI_SETTINGS: dict[str, Any] = {
    "dynamicPrompter": {
        "enabled": True,
        "silenceSeconds": 10,
        "cooldownSeconds": 90,
    },
    "crossPlatformViralEngine": {
        "enabled": True,
        "autoPost": False,
        "cooldownSeconds": 180,
        "minHypeScore": 75,
    },
    "sentimentShield": {
        "enabled": True,
        "nuanceDetection": True,
        "antiHateRaid": {
            "enabled": True,
            "windowSeconds": 2,
            "joinThreshold": 25,
        },
    },
    "contentFarm": {
        "enabled": True,
        "autoCaptionStyle": "hormozi",
        "verticalCropTarget": "face_plus_gameplay",
    },
    "streamDoctor": {
        "enabled": True,
        "droppedFramesWarn": 120,
        "highBitrateKbps": 6000,
        "micSourceName": "Mic/Aux",
    },
    "spoilerFilter": {
        "enabled": True,
        "action": "blur_for_streamer",  # blur_for_streamer | delete
        "keywords": [
            "ending",
            "final boss",
            "phase 2",
            "secret ending",
            "twist",
            "spoiler",
            "solution",
            "puzzle answer",
        ],
    },
    "empathyGuard": {
        "enabled": True,
        "autoWhisperResources": True,
    },
    "audioSafeMode": {
        "enabled": True,
        "desktopAudioSource": "Desktop Audio",
        "copyrightThreshold": 0.8,
    },
    "tosBodyguard": {
        "enabled": True,
        "riskThreshold": 0.82,
        "safeSceneName": "BRB",
        "autoTriggerPanicMode": True,
    },
    "audienceAgent": {
        "enabled": True,
        "pollOptionCount": 4,
        "backseatStyle": "concise",
    },
}


EMPATHY_TERMS = {
    "suicide",
    "kill myself",
    "end my life",
    "self harm",
    "self-harm",
    "abuse",
    "trauma",
    "depressed",
    "depression",
    "panic attack",
}

TARGETED_HATE_PATTERNS = [
    re.compile(r"\bi\s+hate\s+you\b"),
    re.compile(r"\bkill\s+yourself\b"),
    re.compile(r"\bkys\b"),
    re.compile(r"\byou\s+(are|r)\s+(trash|garbage|pathetic|stupid|idiot)\b"),
]

NON_TARGETED_FRUSTRATION_PATTERNS = [
    re.compile(r"\bi\s+hate\s+(this|that|the)\s+(level|boss|game|map|quest|puzzle)\b"),
    re.compile(r"\bthis\s+(level|boss|game|map|quest|puzzle)\s+is\s+(awful|trash|bad|annoying)\b"),
]

ACTIVITY_EVENT_TYPES = {
    "chat_message",
    "chat",
    "voice_activity",
    "command",
    "command_executed",
    "clip_created",
    "moment_score",
}

JOIN_EVENT_TYPES = {
    "user_join",
    "chat_join",
    "follow",
    "viewer_join",
}

AUDIO_EVENT_TYPES = {
    "music_detected",
    "audio_track",
    "now_playing",
}

VISION_EVENT_TYPES = {
    "vision_tos_scan",
    "vision_frame_analysis",
    "camera_frame_analysis",
    "video_frame_analysis",
}

PROHIBITED_LABELS = {
    "nudity",
    "explicit_nudity",
    "graphic_violence",
    "self_harm",
    "extremist_symbol",
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _merge(base: dict, override: dict | None) -> dict:
    merged = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _safe_lower(value: str | None) -> str:
    return (value or "").strip().lower()


def _keywords_from_messages(messages: list[str], limit: int = 6) -> list[str]:
    stop = {
        "this", "that", "with", "from", "have", "your", "about", "there", "their",
        "they", "just", "really", "were", "will", "would", "could", "should",
        "what", "when", "where", "which", "why", "how",
    }
    words: list[str] = []
    for msg in messages:
        words.extend([w for w in re.findall(r"\b[a-z0-9]{4,}\b", _safe_lower(msg)) if w not in stop])
    counts = Counter(words)
    return [word for word, _ in counts.most_common(limit)]


def _estimate_virality(
    *,
    message_velocity: float = 0.0,
    laughter_markers: int = 0,
    intensity: float = 0.0,
    pacing: float = 0.5,
) -> int:
    velocity_factor = min(1.0, max(0.0, message_velocity / 20.0))
    laughter_factor = min(1.0, max(0.0, laughter_markers / 6.0))
    intensity_factor = min(1.0, max(0.0, intensity))
    pacing_factor = min(1.0, max(0.0, pacing))
    score = (
        velocity_factor * 0.35
        + laughter_factor * 0.2
        + intensity_factor * 0.25
        + pacing_factor * 0.2
    )
    return int(max(1, min(100, round(score * 100))))


class StreamerAISuite:
    def __init__(self):
        self._state: dict[int, dict[str, Any]] = defaultdict(self._new_state)

    def _new_state(self) -> dict[str, Any]:
        now = _now_utc()
        return {
            "last_activity_at": now,
            "last_prompt_at": now - timedelta(hours=1),
            "last_viral_post_at": now - timedelta(hours=1),
            "join_events": deque(maxlen=500),
            "recent_messages": deque(maxlen=50),
            "prompt_index": 0,
            "last_dmca_action_at": now - timedelta(hours=1),
        }

    def _config(self, settings_json: dict | None) -> dict:
        settings = settings_json or {}
        suite_settings = settings.get("streamerAiSuite") or {}
        return _merge(DEFAULT_STREAMER_AI_SETTINGS, suite_settings)

    def summarize_status(self, streamer_id: int, settings_json: dict | None = None) -> dict:
        cfg = self._config(settings_json)
        state = self._state[streamer_id]
        return {
            "streamer_id": streamer_id,
            "last_activity_at": state["last_activity_at"].isoformat(),
            "last_prompt_at": state["last_prompt_at"].isoformat(),
            "last_viral_post_at": state["last_viral_post_at"].isoformat(),
            "recent_chat_samples": list(state["recent_messages"])[-5:],
            "config": cfg,
        }

    def _classify_toxic_intent(self, message: str, cfg: dict) -> dict | None:
        if not cfg["sentimentShield"]["enabled"]:
            return None
        text = _safe_lower(message)
        if not text:
            return None

        for pattern in NON_TARGETED_FRUSTRATION_PATTERNS:
            if pattern.search(text):
                return {
                    "category": "frustration",
                    "action": "allow",
                    "reason": "Non-targeted frustration detected; likely gameplay venting.",
                    "confidence": 0.82,
                }

        for pattern in TARGETED_HATE_PATTERNS:
            if pattern.search(text):
                return {
                    "category": "targeted_hate",
                    "action": "ban_or_timeout",
                    "reason": "Targeted harassment intent detected.",
                    "confidence": 0.9,
                }
        return None

    def _detect_spoiler(self, message: str, cfg: dict) -> dict | None:
        spoiler_cfg = cfg["spoilerFilter"]
        if not spoiler_cfg["enabled"]:
            return None
        text = _safe_lower(message)
        if not text:
            return None
        keywords = [str(k).strip().lower() for k in spoiler_cfg.get("keywords", []) if str(k).strip()]
        for token in keywords:
            if token in text:
                return {
                    "token": token,
                    "action": spoiler_cfg.get("action", "blur_for_streamer"),
                    "reason": f"Potential spoiler term detected: {token}",
                }
        return None

    def _detect_empathy_event(self, message: str, cfg: dict) -> dict | None:
        empathy_cfg = cfg["empathyGuard"]
        if not empathy_cfg["enabled"]:
            return None
        text = _safe_lower(message)
        if not text:
            return None
        for term in EMPATHY_TERMS:
            if term in text:
                whisper = (
                    "We care about you. If you're in immediate danger, call emergency services now. "
                    "US 988 Lifeline: call or text 988."
                )
                return {
                    "term": term,
                    "auto_whisper": bool(empathy_cfg.get("autoWhisperResources", True)),
                    "resource_message": whisper,
                }
        return None

    def _detect_raid(self, streamer_id: int, event_type: str, username: str | None, cfg: dict) -> dict | None:
        raid_cfg = cfg["sentimentShield"]["antiHateRaid"]
        if not (cfg["sentimentShield"]["enabled"] and raid_cfg["enabled"]):
            return None
        if event_type not in JOIN_EVENT_TYPES:
            return None

        state = self._state[streamer_id]
        now = _now_utc()
        window_seconds = max(1, int(raid_cfg.get("windowSeconds", 2)))
        threshold = max(5, int(raid_cfg.get("joinThreshold", 25)))

        state["join_events"].append((now, _safe_lower(username)))
        cutoff = now - timedelta(seconds=window_seconds)
        recent = [entry for entry in state["join_events"] if entry[0] >= cutoff]
        suspicious = [
            name for _, name in recent
            if name and re.search(r"(bot|tmp|user\d{4,}|^[a-z]{1,3}\d{3,})", name)
        ]
        if len(recent) >= threshold or (len(recent) >= threshold // 2 and len(suspicious) >= threshold // 3):
            return {
                "join_count": len(recent),
                "suspicious_count": len(suspicious),
                "window_seconds": window_seconds,
            }
        return None

    def _detect_viral_trigger(
        self,
        streamer_id: int,
        moment_score: dict | None,
        payload: dict | None,
        cfg: dict,
    ) -> dict | None:
        engine = cfg["crossPlatformViralEngine"]
        if not engine["enabled"]:
            return None

        moment = moment_score or {}
        p = payload or {}
        hype_score = float(moment.get("score") or p.get("hype_score") or p.get("virality_hint") or 0.0)
        confidence = _safe_lower(moment.get("confidence") or p.get("confidence"))
        min_score = float(engine.get("minHypeScore", 75))
        if hype_score < min_score and confidence != "high":
            return None

        state = self._state[streamer_id]
        now = _now_utc()
        cooldown = max(30, int(engine.get("cooldownSeconds", 180)))
        if (now - state["last_viral_post_at"]).total_seconds() < cooldown:
            return None
        state["last_viral_post_at"] = now
        return {
            "hype_score": hype_score,
            "confidence": confidence or "medium",
            "auto_post": bool(engine.get("autoPost", False)),
        }

    def _detect_dmca(self, streamer_id: int, event_type: str, payload: dict | None, cfg: dict) -> dict | None:
        dmca = cfg["audioSafeMode"]
        if not dmca["enabled"]:
            return None
        if event_type not in AUDIO_EVENT_TYPES:
            return None

        p = payload or {}
        confidence = float(p.get("copyright_confidence", p.get("match_confidence", 0.0)) or 0.0)
        title = str(p.get("track_title") or p.get("title") or "").strip()
        artist = str(p.get("artist") or "").strip()
        if confidence < float(dmca.get("copyrightThreshold", 0.8)) and not (title and artist):
            return None

        state = self._state[streamer_id]
        now = _now_utc()
        if (now - state["last_dmca_action_at"]).total_seconds() < 30:
            return None
        state["last_dmca_action_at"] = now
        return {
            "confidence": confidence,
            "track_title": title,
            "artist": artist,
            "source": dmca.get("desktopAudioSource", "Desktop Audio"),
        }
    def _detect_tos_risk(self, event_type: str, payload: dict | None, cfg: dict) -> dict | None:
        bodyguard = cfg["tosBodyguard"]
        if not bodyguard["enabled"]:
            return None
        if event_type not in VISION_EVENT_TYPES:
            return None

        p = payload or {}
        risk_score = float(p.get("tos_risk_score", p.get("risk_score", p.get("nsfw_score", 0.0))) or 0.0)
        labels = [str(x).strip().lower() for x in (p.get("labels") or p.get("detected_labels") or []) if str(x).strip()]
        flagged_labels = [label for label in labels if label in PROHIBITED_LABELS]
        threshold = float(bodyguard.get("riskThreshold", 0.82))

        if risk_score < threshold and not flagged_labels:
            return None

        return {
            "risk_score": risk_score,
            "threshold": threshold,
            "labels": labels[:12],
            "flagged_labels": flagged_labels,
            "safe_scene": bodyguard.get("safeSceneName", "BRB"),
            "auto_trigger_panic": bool(bodyguard.get("autoTriggerPanicMode", True)),
        }
    def process_event(
        self,
        *,
        streamer_id: int,
        settings_json: dict | None,
        platform: str,
        event_type: str,
        username: str | None,
        message: str | None,
        payload: dict | None = None,
        moment_score: dict | None = None,
    ) -> list[dict]:
        cfg = self._config(settings_json)
        state = self._state[streamer_id]
        now = _now_utc()
        event_type_value = _safe_lower(event_type)
        message_value = message or ""

        if event_type_value in ACTIVITY_EVENT_TYPES:
            state["last_activity_at"] = now
        if message_value:
            state["recent_messages"].append(message_value[:220])

        signals: list[dict] = []

        toxic = self._classify_toxic_intent(message_value, cfg) if message_value else None
        if toxic:
            should_enforce = toxic["action"] != "allow" and float(toxic.get("confidence", 0.0)) >= 0.88
            signals.append(
                {
                    "feature": "sentiment_shield",
                    "event_type": "sentiment_shield_intent",
                    "severity": "high" if toxic["action"] != "allow" else "info",
                    "title": "Sentiment Shield",
                    "message": toxic["reason"],
                    "data": toxic,
                    "create_command": toxic["action"] != "allow",
                    "command_intent": "moderation_auto_action" if toxic["action"] != "allow" else None,
                    "command_payload": (
                        {
                            "action": "timeout" if toxic["action"] == "ban_or_timeout" else toxic["action"],
                            "username": username or "viewer",
                            "duration_seconds": 600,
                            "reason": toxic["reason"],
                        }
                        if toxic["action"] != "allow"
                        else None
                    ),
                    "auto_execute": should_enforce,
                }
            )

        spoiler = self._detect_spoiler(message_value, cfg) if message_value else None
        if spoiler:
            signals.append(
                {
                    "feature": "spoiler_filter",
                    "event_type": "spoiler_filtered",
                    "severity": "medium",
                    "title": "Spoiler Filter",
                    "message": spoiler["reason"],
                    "data": spoiler,
                }
            )

        empathy = self._detect_empathy_event(message_value, cfg) if message_value else None
        if empathy:
            signals.append(
                {
                    "feature": "empathy_guard",
                    "event_type": "empathy_guard_triggered",
                    "severity": "medium",
                    "title": "Empathy Guard",
                    "message": "Heavy emotional message detected and isolated from main flow.",
                    "data": empathy,
                }
            )

        raid = self._detect_raid(streamer_id, event_type_value, username, cfg)
        if raid:
            signals.append(
                {
                    "feature": "sentiment_shield",
                    "event_type": "anti_hate_raid_triggered",
                    "severity": "high",
                    "title": "Anti-Hate Raid",
                    "message": f"Raid pattern detected ({raid['join_count']} joins in {raid['window_seconds']}s).",
                    "data": {
                        **raid,
                        "recommended_action": "lock_chat_follower_only",
                    },
                    "create_command": True,
                    "command_intent": "lock_chat_follower_only",
                    "command_payload": {
                        "follower_only_minutes": 10,
                        "slow_mode_seconds": 5,
                        "block_links": True,
                    },
                    "auto_execute": True,
                }
            )

        viral = self._detect_viral_trigger(streamer_id, moment_score, payload, cfg)
        if viral:
            post_text = "Insane clutch happening right now. Join live before you miss it."
            signals.append(
                {
                    "feature": "cross_platform_viral_engine",
                    "event_type": "viral_engine_moment",
                    "severity": "info",
                    "title": "Cross-Platform Viral Engine",
                    "message": post_text,
                    "data": viral,
                    "create_command": True,
                    "command_intent": "crosspost_hype_update",
                }
            )

        dmca = self._detect_dmca(streamer_id, event_type_value, payload, cfg)
        if dmca:
            signals.append(
                {
                    "feature": "audio_safe_mode",
                    "event_type": "audio_safe_mode_triggered",
                    "severity": "high",
                    "title": "Audio Safe Mode",
                    "message": "Potential copyrighted audio detected. Recommended mute on stream output.",
                    "data": dmca,
                    "auto_obs_mute": True,
                }
            )

        tos_risk = self._detect_tos_risk(event_type_value, payload, cfg)
        if tos_risk:
            signals.append(
                {
                    "feature": "tos_bodyguard",
                    "event_type": "tos_bodyguard_triggered",
                    "severity": "critical",
                    "title": "TOS Bodyguard",
                    "message": "Potential policy-violating visual content detected. Triggering safety scene.",
                    "data": tos_risk,
                    "create_command": True,
                    "command_intent": "panic_mode",
                    "command_payload": {"panic_scene": tos_risk.get("safe_scene", "BRB")},
                    "auto_execute": bool(tos_risk.get("auto_trigger_panic", True)),
                }
            )

        return signals

    def tick(
        self,
        *,
        streamer_id: int,
        settings_json: dict | None,
        current_scene: str | None = None,
        obs_stats: dict | None = None,
    ) -> list[dict]:
        cfg = self._config(settings_json)
        state = self._state[streamer_id]
        now = _now_utc()
        signals: list[dict] = []

        # 1) Dynamic Prompter
        prompter = cfg["dynamicPrompter"]
        if prompter["enabled"]:
            silence_sec = max(5, int(prompter.get("silenceSeconds", 10)))
            cooldown_sec = max(30, int(prompter.get("cooldownSeconds", 90)))
            silent_for = (now - state["last_activity_at"]).total_seconds()
            since_prompt = (now - state["last_prompt_at"]).total_seconds()
            if silent_for >= silence_sec and since_prompt >= cooldown_sec:
                prompt_templates = [
                    "You just had a rough sequence. Ask chat what loadout they would switch to.",
                    "Trivia break: ask chat if they know a hidden mechanic in this game.",
                    "Remind chat about your next stream schedule and ask who is coming.",
                ]
                idx = state["prompt_index"] % len(prompt_templates)
                state["prompt_index"] += 1
                state["last_prompt_at"] = now
                signals.append(
                    {
                        "feature": "dynamic_prompter",
                        "event_type": "dynamic_prompt_ready",
                        "severity": "info",
                        "title": "Dynamic Prompter",
                        "message": prompt_templates[idx],
                        "data": {
                            "silent_for_seconds": int(silent_for),
                            "scene": current_scene or "Unknown",
                        },
                        "create_command": False,
                    }
                )

        # 2) Stream Doctor
        doctor = cfg["streamDoctor"]
        if doctor["enabled"] and obs_stats:
            dropped = int(obs_stats.get("dropped_frames", 0) or 0)
            bitrate = int(obs_stats.get("bitrate", 0) or 0)
            mic_muted = bool(obs_stats.get("mic_muted", False))
            dropped_warn = max(30, int(doctor.get("droppedFramesWarn", 120)))
            high_bitrate = max(2500, int(doctor.get("highBitrateKbps", 6000)))

            if dropped >= dropped_warn:
                recommended = min(4500, max(2500, high_bitrate - 1000))
                signals.append(
                    {
                        "feature": "stream_doctor",
                        "event_type": "stream_doctor_bitrate_warning",
                        "severity": "high",
                        "title": "Stream Doctor",
                        "message": (
                            f"Dropped frames detected ({dropped}). "
                            f"Suggested bitrate: {recommended} kbps."
                        ),
                        "data": {
                            "dropped_frames": dropped,
                            "current_bitrate": bitrate,
                            "recommended_bitrate": recommended,
                        },
                    }
                )

            if mic_muted:
                signals.append(
                    {
                        "feature": "stream_doctor",
                        "event_type": "stream_doctor_mic_muted_alert",
                        "severity": "critical",
                        "title": "Stream Doctor",
                        "message": "MIC MUTED",
                        "data": {
                            "overlay_style": "flash_red_border",
                            "source": doctor.get("micSourceName", "Mic/Aux"),
                        },
                    }
                )

        return signals

    def build_seo_suggestions(
        self,
        *,
        game: str,
        messages: list[str],
        streamer_name: str | None = None,
    ) -> dict:
        game_name = game.strip() or "Gaming"
        keywords = _keywords_from_messages(messages, limit=6)
        trend_hint = ", ".join(keywords[:3]) if keywords else "ranked, challenge, live"
        creator = streamer_name or "Streamer"

        titles = [
            f"{creator} LIVE: {game_name} Clutch Run + Chat Challenges",
            f"{game_name} Ranked Push Live | High Risk Plays + Viewer Calls",
            f"{game_name} No-Spoiler Journey | Real-Time Decisions with Chat",
        ]
        tags = [game_name.lower(), "live", "gaming", "clutch", "stream", *keywords[:6]]
        description = (
            f"Live {game_name} stream with real-time chat moments, highlights, and tactical decisions. "
            f"Current trend focus: {trend_hint}."
        )
        return {
            "titles": titles,
            "tags": tags[:12],
            "description": description,
            "trend_keywords": keywords[:6],
        }

    def analyze_content_farm_clip(
        self,
        *,
        transcript: str = "",
        message_velocity: float = 0.0,
        laughter_markers: int = 0,
        intensity: float = 0.0,
        pacing: float = 0.5,
    ) -> dict:
        virality = _estimate_virality(
            message_velocity=message_velocity,
            laughter_markers=laughter_markers,
            intensity=intensity,
            pacing=pacing,
        )
        lines = [line.strip() for line in re.split(r"[.!?]", transcript or "") if line.strip()]
        captions = lines[:6] if lines else ["Big moment here", "Chat exploded", "Stay for the finish"]
        return {
            "virality_score": virality,
            "crop_mode": "9:16_face_plus_gameplay",
            "caption_style": "hormozi",
            "captions": captions,
        }

    def build_dynamic_poll(
        self,
        *,
        topic: str,
        recent_messages: list[str],
        option_count: int = 4,
    ) -> dict:
        cleaned_topic = topic.strip() or "next move"
        option_count = max(2, min(option_count, 5))
        keywords = _keywords_from_messages(recent_messages, limit=option_count + 2)

        options: list[str] = []
        for keyword in keywords:
            label = keyword.replace("_", " ").strip().title()
            if label and label not in options:
                options.append(label)
            if len(options) >= option_count:
                break

        while len(options) < option_count:
            defaults = ["Aggressive Play", "Safe Play", "Challenge Route", "Community Pick", "Chaos Option"]
            candidate = defaults[len(options) % len(defaults)]
            if candidate not in options:
                options.append(candidate)

        return {
            "topic": cleaned_topic,
            "question": f"What should we do next for {cleaned_topic}?",
            "options": options[:option_count],
        }

    def build_backseating_advice(
        self,
        *,
        game: str,
        context: str = "",
        champion: str | None = None,
    ) -> dict:
        game_name = game.strip() or "current game"
        context_text = (context or "").strip()
        champion_name = (champion or "").strip()

        suggestions = [
            "Stabilize first: avoid coin-flip fights for the next 90 seconds.",
            "Call out one clear objective to chat and commit to that path.",
            "Track cooldowns/resources before forcing the next engage.",
        ]

        lowered_game = game_name.lower()
        if "league" in lowered_game or "lol" in lowered_game:
            if champion_name:
                suggestions.insert(0, f"For {champion_name}: prioritize wave control before all-ins.")
            suggestions.append("Play around vision: contest only with ward coverage and numbers advantage.")
        elif "valorant" in lowered_game or "cs" in lowered_game:
            suggestions.append("Use utility before peeking to improve trade probability.")
        elif "fortnite" in lowered_game or "apex" in lowered_game:
            suggestions.append("Reset positioning after each fight before looting greedily.")

        return {
            "game": game_name,
            "context": context_text,
            "champion": champion_name or None,
            "advice": suggestions[:5],
        }

    def build_post_stream_report(
        self,
        *,
        events: list[dict],
        clips: list[dict],
        commands: list[dict],
        viewer_actions: list[dict] | None = None,
    ) -> dict:
        viewer_actions = viewer_actions or []
        total_events = len(events)
        if total_events == 0:
            return {
                "summary": "No stream events captured in this window.",
                "kpis": {
                    "events_per_minute": 0.0,
                    "retention_estimate_pct": 0.0,
                    "clip_approval_rate_pct": 0.0,
                    "command_execution_rate_pct": 0.0,
                    "viewer_action_execution_rate_pct": 0.0,
                    "viewer_credits_spent": 0,
                },
                "highlights": [],
                "dropoff_windows": [],
                "recommendations": ["Ensure ingestion is connected before next stream."],
            }

        def _parse_ts(value: Any) -> datetime | None:
            if not value:
                return None
            try:
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return None

        bucket_counts: dict[str, int] = Counter()
        event_type_counts: dict[str, int] = Counter()
        parsed_timestamps: list[datetime] = []
        chat_events = 0
        engagement_events = 0
        engagement_drivers = {
            "chat_message",
            "viewer_msg",
            "follow",
            "sub",
            "donation",
            "superchat",
            "raid",
            "viewer_clip_requested",
            "highlight_detected",
            "clip_saved",
        }
        for event in events:
            ts = _parse_ts(event.get("created_at"))
            slot = ts.strftime("%Y-%m-%d %H:%M") if ts else "unknown"
            bucket_counts[slot] += 1
            event_type = str(event.get("event_type") or "unknown")
            event_type_counts[event_type] += 1
            if ts:
                parsed_timestamps.append(ts)
            if event_type in {"chat_message", "viewer_msg"}:
                chat_events += 1
            if event_type in engagement_drivers:
                engagement_events += 1

        parsed_timestamps.sort()
        if parsed_timestamps:
            active_seconds = max((parsed_timestamps[-1] - parsed_timestamps[0]).total_seconds(), 60.0)
            active_minutes = max(1.0, active_seconds / 60.0)
        else:
            active_minutes = max(1.0, len(bucket_counts))

        midpoint_count = len(parsed_timestamps) // 2
        if midpoint_count > 0 and len(parsed_timestamps) >= 6:
            first_half = parsed_timestamps[:midpoint_count]
            second_half = parsed_timestamps[midpoint_count:]
            first_span_minutes = max(1.0, (first_half[-1] - first_half[0]).total_seconds() / 60.0)
            second_span_minutes = max(1.0, (second_half[-1] - second_half[0]).total_seconds() / 60.0)
            first_rate = len(first_half) / first_span_minutes
            second_rate = len(second_half) / second_span_minutes
            retention_estimate = max(0.0, min(1.0, second_rate / max(first_rate, 0.001)))
        else:
            retention_estimate = 1.0

        ranked_buckets = sorted(bucket_counts.items(), key=lambda x: x[1], reverse=True)
        highlights = [{"window": slot, "activity": count} for slot, count in ranked_buckets[:3] if slot != "unknown"]

        avg_activity = sum(bucket_counts.values()) / max(len(bucket_counts), 1)
        low_cutoff = max(1, int(avg_activity * 0.45))
        dropoff_windows = [
            {
                "window": slot,
                "activity": count,
                "dropoff_pct_vs_avg": round(max(0.0, 1.0 - (count / max(avg_activity, 1.0))) * 100, 1),
            }
            for slot, count in sorted(bucket_counts.items(), key=lambda x: x[0])
            if count <= low_cutoff and slot != "unknown"
        ][:3]

        clip_count = len(clips)
        approved_clips = sum(1 for clip in clips if str(clip.get("status", "")).lower() == "approved")
        rejected_clips = sum(1 for clip in clips if str(clip.get("status", "")).lower() == "rejected")
        executed_commands = sum(1 for cmd in commands if str(cmd.get("status", "")).lower() == "executed")
        command_count = len(commands)
        clip_approval_rate = (approved_clips / clip_count) if clip_count else 0.0
        command_execution_rate = (executed_commands / command_count) if command_count else 0.0

        action_type_counts = Counter(str(item.get("action_type") or "unknown") for item in viewer_actions)
        viewer_action_total = len(viewer_actions)
        viewer_action_executed = sum(
            1 for item in viewer_actions if str(item.get("status") or "").lower() in {"executed"}
        )
        viewer_action_execution_rate = (
            viewer_action_executed / viewer_action_total if viewer_action_total else 0.0
        )
        viewer_credits_spent = sum(int(item.get("cost") or 0) for item in viewer_actions)

        recommendations: list[str] = []
        if clip_count < 3:
            recommendations.append("Clip volume was low. Lower hype threshold or enable more aggressive auto-clipping.")
        if approved_clips < max(1, clip_count // 2):
            recommendations.append("Approval ratio is low. Tune clip quality scoring before export.")
        if executed_commands < max(1, len(commands) // 3):
            recommendations.append("Execution throughput is low. Review command policy thresholds and auto-approval tiers.")
        if retention_estimate < 0.75:
            recommendations.append("Engagement drops later in stream. Schedule a planned format switch before the first dropoff window.")
        if viewer_action_total > 0 and viewer_action_execution_rate < 0.7:
            recommendations.append("Viewer action execution is weak. Prioritize queue throughput and cooldown tuning.")
        top_event = event_type_counts.most_common(1)[0][0] if event_type_counts else "events"
        recommendations.append(f"Top engagement driver was '{top_event}'. Lean next stream format toward it.")

        return {
            "summary": (
                f"Captured {total_events} events over {active_minutes:.1f} minutes, "
                f"{clip_count} clips ({approved_clips} approved), and {command_count} commands."
            ),
            "kpis": {
                "events_per_minute": round(total_events / max(active_minutes, 1.0), 2),
                "chat_events": chat_events,
                "engagement_events": engagement_events,
                "retention_estimate_pct": round(retention_estimate * 100, 1),
                "clip_approval_rate_pct": round(clip_approval_rate * 100, 1),
                "command_execution_rate_pct": round(command_execution_rate * 100, 1),
                "viewer_action_execution_rate_pct": round(viewer_action_execution_rate * 100, 1),
                "viewer_credits_spent": int(viewer_credits_spent),
                "clips_rejected": rejected_clips,
            },
            "highlights": highlights,
            "dropoff_windows": dropoff_windows,
            "event_type_breakdown": dict(event_type_counts),
            "viewer_action_breakdown": dict(action_type_counts),
            "recommendations": recommendations[:5],
        }


streamer_ai_suite = StreamerAISuite()

