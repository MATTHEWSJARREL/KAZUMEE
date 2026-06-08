"""
IRL Safe Mode - Continuous passive transcription loop for danger phrase detection.
Captures audio continuously when IRL mode is active, transcribes each chunk,
checks for danger phrases, and triggers scene switch on match.
"""
import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Callable, Any

import speech_recognition as sr
import tempfile
import os


logger = logging.getLogger(__name__)


class IRLTranscriber:
    """Passive continuous audio transcription for IRL safety mode."""
    
    def __init__(self, streamer_id: int):
        self.streamer_id = streamer_id
        self.is_active = False
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # Configuration
        self._safe_scene: str = "BRB"
        self._danger_phrases: list[str] = []
        self._chunk_duration_seconds: float = 2.0  # Process audio in 2-second chunks
        
        # Callbacks
        self._on_danger_phrase: Optional[Callable[[str], Any]] = None
        self._on_transcription: Optional[Callable[[str], Any]] = None
        
        # Metrics
        self._last_check_time: float = time.time()
        self._danger_detections: int = 0
        self._chunks_processed: int = 0
    
    def set_callbacks(
        self,
        on_danger_phrase: Optional[Callable[[str], Any]] = None,
        on_transcription: Optional[Callable[[str], Any]] = None,
    ) -> None:
        """Set callback functions for events."""
        with self._lock:
            self._on_danger_phrase = on_danger_phrase
            self._on_transcription = on_transcription
    
    def activate(
        self,
        safe_scene: str = "BRB",
        danger_phrases: Optional[list[str]] = None,
    ) -> dict:
        """Activate IRL mode and start passive transcription loop."""
        with self._lock:
            if self.is_running:
                return {
                    "status": "ok",
                    "message": "IRL transcriber already running",
                    "already_running": True,
                }
            
            self.is_active = True
            self._safe_scene = safe_scene or "BRB"
            self._danger_phrases = danger_phrases or []
            self.is_running = True
        
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._transcription_loop,
            name=f"kazumi-irl-transcriber-{self.streamer_id}",
            daemon=True,
        )
        
        try:
            self._thread.start()
        except Exception as e:
            self.is_running = False
            self._thread = None
            self._stop_event.set()
            logger.error(f"Failed to start IRL transcriber for streamer {self.streamer_id}: {e}")
            raise
        
        logger.info(
            f"IRL transcriber activated for streamer {self.streamer_id}, "
            f"safe_scene={self._safe_scene}, phrases={len(self._danger_phrases)}"
        )
        return {
            "status": "ok",
            "message": f"IRL mode active. Auto-switch to '{self._safe_scene}' on danger phrase.",
            "safe_scene": self._safe_scene,
        }
    
    def deactivate(self, join_timeout: float = 3.0) -> dict:
        """Deactivate IRL mode and stop passive transcription loop."""
        with self._lock:
            if not self.is_running:
                return {"status": "ok", "message": "IRL transcriber not running", "already_stopped": True}
            self.is_running = False
        
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(0.1, float(join_timeout)))
        
        with self._lock:
            self.is_active = False
        
        logger.info(
            f"IRL transcriber deactivated for streamer {self.streamer_id}. "
            f"Detections: {self._danger_detections}, Chunks: {self._chunks_processed}"
        )
        return {
            "status": "ok",
            "message": "IRL mode deactivated",
            "stats": {
                "danger_detections": self._danger_detections,
                "chunks_processed": self._chunks_processed,
            },
        }
    
    def get_status(self) -> dict:
        """Get current IRL transcriber status."""
        with self._lock:
            return {
                "is_active": self.is_active,
                "is_running": self.is_running,
                "safe_scene": self._safe_scene,
                "danger_phrases_count": len(self._danger_phrases),
                "danger_detections": self._danger_detections,
                "chunks_processed": self._chunks_processed,
            }
    
    def _transcription_loop(self) -> None:
        """Main transcription loop that runs continuously when IRL mode is active."""
        try:
            import speech_recognition as sr
        except ImportError:
            logger.error("speech_recognition not available for IRL transcription")
            with self._lock:
                self.is_running = False
            return
        
        recognizer = sr.Recognizer()
        chunk_duration = self._chunk_duration_seconds
        
        try:
            with sr.Microphone() as source:
                # Adjust for ambient noise once at startup
                recognizer.adjust_for_ambient_noise(source, duration=0.7)
                logger.info(f"IRL transcriber ready for streamer {self.streamer_id}")
                
                while not self._stop_event.is_set():
                    try:
                        # Capture a short audio chunk (non-blocking with timeout)
                        audio = recognizer.listen(
                            source,
                            timeout=1.0,  # Short timeout to be responsive to stop signal
                            phrase_time_limit=chunk_duration,
                        )
                        
                        # Increment chunk counter
                        with self._lock:
                            self._chunks_processed += 1
                        
                        # STEP 1: Voice fingerprint check BEFORE transcription
                        # This prevents transcription of non-streamer audio, saving API calls
                        if not self._verify_voice_fingerprint(audio):
                            logger.debug(f"IRL: Voice fingerprint check failed for chunk {self._chunks_processed}")
                            continue
                        
                        # STEP 2: Transcribe the audio (only if fingerprint passed)
                        transcript = self._transcribe_audio(audio)
                        if not transcript:
                            continue

                        
                        # STEP 3: Normalize and check for danger phrases
                        transcript_normalized = transcript.lower().strip()
                        if not transcript_normalized:
                            continue
                        
                        # Log transcription for debugging
                        if self._on_transcription:
                            try:
                                self._on_transcription(transcript_normalized)
                            except Exception as e:
                                logger.error(f"IRL transcription callback failed: {e}")
                        
                        # Check each danger phrase
                        for phrase in self._danger_phrases:
                            phrase_lower = phrase.lower().strip()
                            if phrase_lower and phrase_lower in transcript_normalized:
                                logger.warning(
                                    f"IRL: Danger phrase detected: '{phrase}' in '{transcript_normalized}'"
                                )
                                
                                with self._lock:
                                    self._danger_detections += 1
                                    safe_scene = self._safe_scene
                                
                                # Trigger callback for scene switch
                                if self._on_danger_phrase:
                                    try:
                                        self._on_danger_phrase(safe_scene)
                                    except Exception as e:
                                        logger.error(f"IRL danger phrase callback failed: {e}")
                                
                                break  # Only trigger once per chunk
                        
                    except sr.WaitTimeoutError:
                        # No audio detected in timeout window - normal, continue
                        continue
                    except Exception as e:
                        logger.error(f"IRL transcription error: {e}")
                        # Continue listening even on error
                        continue
        
        except Exception as e:
            logger.error(f"IRL transcriber microphone setup failed: {e}")
        finally:
            with self._lock:
                self.is_running = False
                self.is_active = False
            logger.info(f"IRL transcriber thread exiting for streamer {self.streamer_id}")
    
    def _verify_voice_fingerprint(self, audio_data: Any) -> bool:
        """
        Verify audio matches streamer's voice fingerprint BEFORE transcription.
        Returns True if fingerprint matches (or not configured), False if mismatch.
        
        This prevents wasting API calls on transcribing non-streamer audio.
        """
        try:
            from backend.core.voice_fingerprint import verify_voice
            
            # Convert audio to bytes if needed
            if hasattr(audio_data, 'get_wav_data'):
                audio_bytes = audio_data.get_wav_data()
            else:
                audio_bytes = audio_data
            
            # Verify fingerprint
            # For IRL mode we do not have a voice-agent warmup window, so we pass the current time
            # which effectively disables warmup skipping.
            is_valid = verify_voice(self.streamer_id, audio_bytes, agent_start_time=time.time())

            
            if not is_valid:
                logger.debug(f"IRL: Voice fingerprint check rejected audio for streamer {self.streamer_id}")
                return False
            
            return True
        
        except Exception as e:
            logger.warning(f"IRL fingerprint check failed, allowing audio: {e}")
            # Fail open - if fingerprint check fails, continue with transcription
            return True


    def _transcribe_audio(self, audio_data: Any) -> str:
        """Transcribe audio using faster-whisper locally."""
        try:
            from faster_whisper import WhisperModel

            if not hasattr(self, "whisper"):
                # Lazy init to avoid overhead if IRL transcription never starts
                self.whisper = WhisperModel("medium", device="cpu", compute_type="int8")

            wav_bytes = audio_data.get_wav_data()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_bytes)
                tmp_path = tmp.name

            try:
                segments, _info = self.whisper.transcribe(
                    tmp_path,
                    language="en",
                    vad_filter=True,
                    vad_parameters={
                        "min_silence_duration_ms": 600,
                        "speech_pad_ms": 300,
                        "threshold": 0.5,
                    },
                    beam_size=5,
                )
                return " ".join([s.text for s in segments]).strip()
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.error(f"IRL transcription failed: {e}")
            return ""


# Global registry of active IRL transcribers
_irl_transcribers: dict[int, IRLTranscriber] = {}
_irl_transcriber_lock = threading.Lock()



def get_or_create_irl_transcriber(streamer_id: int) -> IRLTranscriber:
    """Get or create IRL transcriber for streamer."""
    with _irl_transcriber_lock:
        if streamer_id not in _irl_transcribers:
            _irl_transcribers[streamer_id] = IRLTranscriber(streamer_id)
        return _irl_transcribers[streamer_id]


def get_irl_transcriber(streamer_id: int) -> Optional[IRLTranscriber]:
    """Get existing IRL transcriber if active."""
    with _irl_transcriber_lock:
        return _irl_transcribers.get(streamer_id)


def start_irl_mode(
    streamer_id: int,
    safe_scene: str = "BRB",
    danger_phrases: Optional[list[str]] = None,
    on_danger_phrase: Optional[Callable] = None,
    on_transcription: Optional[Callable] = None,
) -> dict:
    """Start IRL passive transcription mode."""
    transcriber = get_or_create_irl_transcriber(streamer_id)
    transcriber.set_callbacks(
        on_danger_phrase=on_danger_phrase,
        on_transcription=on_transcription,
    )
    return transcriber.activate(safe_scene=safe_scene, danger_phrases=danger_phrases)


def stop_irl_mode(streamer_id: int) -> dict:
    """Stop IRL passive transcription mode."""
    transcriber = get_irl_transcriber(streamer_id)
    if not transcriber:
        return {"status": "ok", "message": "IRL transcriber not running"}
    return transcriber.deactivate()


def get_irl_status(streamer_id: int) -> dict:
    """Get IRL transcriber status."""
    transcriber = get_irl_transcriber(streamer_id)
    if not transcriber:
        return {"is_active": False, "is_running": False}
    return transcriber.get_status()
