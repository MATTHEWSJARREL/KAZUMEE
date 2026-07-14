from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import threading
from typing import Any, Awaitable, Callable

import speech_recognition as sr

# Voice transcription is optional. If faster-whisper isn't installed,
# the backend should still start (voice features will be disabled).
try:
    from faster_whisper import WhisperModel  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    WhisperModel = None  # type: ignore

import tempfile
import os




CommandCallback = Callable[[str, str, dict[str, Any]], Awaitable[dict[str, Any]]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _extract_wake_command(transcript: str, trigger_word: str, require_wake_word: bool) -> tuple[bool, str]:
    normalized_transcript = _normalize_text(transcript)
    if not normalized_transcript:
        return False, ""

    if not require_wake_word:
        return True, normalized_transcript

    wake = _normalize_text(trigger_word or "kazumi")
    if not wake:
        return True, normalized_transcript

    if normalized_transcript.startswith(wake):
        return True, normalized_transcript[len(wake):].strip()

    wake_with_space = f"{wake} "
    idx = normalized_transcript.find(wake_with_space)
    if idx >= 0:
        return True, normalized_transcript[idx + len(wake_with_space):].strip()

    return False, ""


class VoiceAgentService:
    def __init__(self, loop: asyncio.AbstractEventLoop, command_callback: CommandCallback):
        self._loop = loop
        self._command_callback = command_callback
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._running = False
        self._listening = False
        self._last_error: str | None = None
        self._logs: list[dict[str, Any]] = []
        self._max_logs = 200
        self._config: dict[str, Any] = {}
        # Initialise Whisper model only if dependency is present.
        self.whisper = (
            WhisperModel("medium", device="cpu", compute_type="int8")
            if WhisperModel is not None
            else None
        )


    def _append_log(self, level: str, event: str, message: str, **extra: Any) -> None:
        entry = {
            "time": _now_iso(),
            "level": level,
            "event": event,
            "message": message,
        }
        if extra:
            entry["data"] = extra
        with self._lock:
            self._logs.insert(0, entry)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[: self._max_logs]

    @staticmethod
    def _check_dependencies() -> tuple[bool, str]:
        try:
            import speech_recognition as sr  # noqa: F401
        except Exception as exc:
            return False, f"speech_recognition unavailable: {exc}"
        return True, "ok"

    def status(self) -> dict[str, Any]:
        available, detail = self._check_dependencies()
        with self._lock:
            return {
                "running": self._running,
                "listening": self._listening,
                "available": available,
                "availability_detail": detail,
                "last_error": self._last_error,
                "config": dict(self._config),
                "log_count": len(self._logs),
            }

    def get_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        n = max(1, min(int(limit or 50), 200))
        with self._lock:
            return list(self._logs[:n])

    def start(
        self,
        *,
        trigger_word: str,
        require_wake_word: bool,
        use_ai: bool,
        streamer_id: int,
        phrase_time_limit: int = 6,
        ambient_adjust_seconds: float = 0.7,
        command_timeout_seconds: int = 20,
    ) -> dict[str, Any]:
        available, detail = self._check_dependencies()
        if not available:
            return {
                "status": "error",
                "message": "Voice agent dependencies are missing",
                "detail": detail,
            }

        with self._lock:
            if self._running:
                return {"status": "ok", "message": "Voice agent already running", "already_running": True}

            self._config = {
                "trigger_word": (trigger_word or "Kazumi").strip(),
                "require_wake_word": bool(require_wake_word),
                "use_ai": bool(use_ai),
                "streamer_id": int(streamer_id),
                "phrase_time_limit": max(2, min(int(phrase_time_limit or 6), 12)),
                "ambient_adjust_seconds": max(0.1, min(float(ambient_adjust_seconds or 0.7), 3.0)),
                "command_timeout_seconds": max(3, min(int(command_timeout_seconds or 20), 45)),
            }
            self._running = True
            self._listening = False
            self._last_error = None

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="kazumi-voice-agent", daemon=True)
        self._thread.start()
        self._append_log("info", "voice_agent_start", "Voice agent started", config=self._config)
        return {"status": "ok", "message": "Voice agent started"}

    def stop(self, *, join_timeout: float = 3.0) -> dict[str, Any]:
        with self._lock:
            running = self._running
            self._running = False

        if not running:
            return {"status": "ok", "message": "Voice agent already stopped", "already_stopped": True}

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(0.2, float(join_timeout)))
        with self._lock:
            self._listening = False
        self._append_log("info", "voice_agent_stop", "Voice agent stopped")
        return {"status": "ok", "message": "Voice agent stopped"}

    def _set_listening(self, value: bool) -> None:
        with self._lock:
            self._listening = bool(value)

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message
        self._append_log("error", "voice_agent_error", message)

    def _run_loop(self) -> None:
        try:
            import speech_recognition as sr
        except Exception as exc:
            self._set_error(f"Voice dependencies unavailable: {exc}")
            with self._lock:
                self._running = False
                self._listening = False
            return

        recognizer = sr.Recognizer()
        config = dict(self._config)
        trigger_word = config.get("trigger_word", "Kazumi")
        require_wake_word = bool(config.get("require_wake_word", True))
        streamer_id = config.get("streamer_id")
        agent_start_time = __import__("time").time()


        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=float(config.get("ambient_adjust_seconds", 0.7)))
                self._append_log("info", "voice_agent_ready", "Microphone calibrated and listening")
                self._set_listening(True)

                while not self._stop_event.is_set():
                    try:
                        audio = recognizer.listen(
                            source,
                            timeout=1.0,
                            phrase_time_limit=float(config.get("phrase_time_limit", 6)),
                        )
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as exc:
                        self._set_error(f"Microphone listen failed: {exc}")
                        continue

                    # CRITICAL: Fingerprint check BEFORE transcription
                    # Verify voice is streamer's voice to avoid wasting Groq API calls on strangers
                    # During the initial agent warmup we skip fingerprint checks entirely.
                    if streamer_id is not None and not self._verify_streamer_fingerprint(audio, streamer_id, agent_start_time):

                        self._append_log("info", "voice_fingerprint_rejected", "Voice fingerprint verification failed")
                        continue  # Silent rejection - do not transcribe


                    transcript = self.transcribe_audio(audio)
                    if not transcript:
                        continue


                    matched, command = _extract_wake_command(transcript, trigger_word, require_wake_word)
                    self._append_log("info", "voice_transcript", transcript, matched=matched)
                    if not matched:
                        continue
                    if not command:
                        self._append_log("info", "voice_wakeword_only", "Wake word heard without command")
                        continue

                    # Immediate streamer feedback hook:
                    # If the voice command is a clipping-related command, notify frontend
                    # before the backend starts saving to the replay buffer.
                    try:
                        cmd_lc = (command or "").lower()
                        if "save_replay_buffer" in cmd_lc or "replay" in cmd_lc or "clip" in cmd_lc:
                            asyncio.run_coroutine_threadsafe(
                                self._command_callback("__notify_clipping__", transcript, {**config, "_notify_only": True}),
                                self._loop,
                            )
                    except Exception:
                        pass

                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self._command_callback(command, transcript, config),
                            self._loop,
                        )
                        result = future.result(timeout=float(config.get("command_timeout_seconds", 20)))
                        self._append_log("info", "voice_command_executed", "Command executed", command=command, result=result)
                    except Exception as exc:
                        self._set_error(f"Voice command dispatch failed: {exc}")
        except Exception as exc:
            self._set_error(f"Microphone startup failed: {exc}")
        finally:
            self._set_listening(False)
            with self._lock:
                self._running = False
    def transcribe_audio(self, audio_data: Any) -> str:
        """Transcribe audio using faster-whisper locally (if available)."""
        if self.whisper is None:
            self._set_error("faster-whisper not installed; transcription disabled")
            return ""

        try:
            wav_bytes = audio_data.get_wav_data()


            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_bytes)
                tmp_path = tmp.name

            try:
                segments, info = self.whisper.transcribe(
                    tmp_path,
                    language="en",
                    vad_filter=True,
                    vad_parameters={
                        "min_silence_duration_ms": 600,
                        "speech_pad_ms": 300,
                        "threshold": 0.35,
                    },
                    beam_size=5,
                )

                return " ".join([s.text for s in segments]).strip()
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            self._set_error(f"Transcription failed: {e}")
            self._append_log("error", "transcription_failed", f"Transcription failed: {e}")
            return ""


    
    def _verify_streamer_fingerprint(self, audio: Any, streamer_id: int, agent_start_time: float) -> bool: # type: ignore

        """
        Verify audio matches streamer's voice fingerprint BEFORE transcription.
        Returns True if fingerprint matches, False if mismatch or check fails open.
        This prevents Groq API calls for non-streamer audio.
        """
        try:
            from backend.core.voice_fingerprint import verify_voice
            
            # Convert audio to bytes if needed
            if hasattr(audio, 'get_wav_data'):
                audio_bytes = audio.get_wav_data()
            else:
                audio_bytes = audio
            
            # Verify fingerprint - returns False with log only, no sound/visual feedback
            is_valid = verify_voice(streamer_id, audio_bytes, agent_start_time)

            
            if not is_valid:
                # Silent rejection - no sound, no visual feedback to end-user
                # Only logged internally
                return False
            
            return True
        
        except Exception as e:
            # Fail open - if fingerprint check fails, continue with transcription
            # Better to transcribe a stranger than to block the streamer
            self._append_log("warning", "voice_fingerprint_error", f"Fingerprint check error: {e}")
            return True
