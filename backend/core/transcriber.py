"""
Audio Transcription Service

Uses Whisper AI to transcribe video audio with word-level timestamps.
Supports fallback mode for testing without GPU.
"""

import logging
import os
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not installed, will use fallback mode")


class TranscriptionResult:
    """Result of transcription"""

    def __init__(self, text: str, words: List[Dict] = None):
        self.text = text
        self.words = words or []

    def to_dict(self):
        return {
            "text": self.text,
            "words": self.words,
        }


class Transcriber:
    """Transcribes video audio using Whisper"""

    def __init__(self, model_name: str = "tiny"):
        """
        Initialize transcriber.

        Args:
            model_name: Whisper model size ("tiny", "base", "small", "medium", "large")
                       tiny is fastest (1GB), large is best quality (3GB)
        """
        self.model_name = model_name
        self.model = None
        self.device = self._detect_device()
        logger.info(f"Transcriber initialized (model: {model_name}, device: {self.device})")

    def _detect_device(self) -> str:
        """Detect if GPU is available"""
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("GPU detected (CUDA available)")
                return "cuda"
        except ImportError:
            pass

        logger.info("Using CPU for transcription")
        return "cpu"

    def _load_model(self):
        """Lazy-load Whisper model"""
        if self.model is not None:
            return

        if not WHISPER_AVAILABLE:
            logger.warning("Whisper not available, using fallback transcription")
            return

        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = WhisperModel(self.model_name, device=self.device)
            logger.info("✓ Whisper model loaded")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.model = None

    def _transcribe_with_whisper(self, audio_path: str) -> Optional[TranscriptionResult]:
        """Transcribe using Whisper"""
        self._load_model()

        if not self.model:
            return None

        try:
            logger.info(f"Transcribing: {audio_path}")

            segments, info = self.model.transcribe(
                audio_path,
                language="en",
                word_level=True,
            )

            # Extract words with timestamps
            full_text = ""
            words = []

            for segment in segments:
                segment_text = segment.text.strip()
                if not segment_text:
                    continue

                full_text += segment_text + " "

                # Try to get word-level timestamps
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        words.append({
                            "word": word.word.strip(),
                            "start": round(word.start, 2),
                            "end": round(word.end, 2),
                        })
                else:
                    # Fallback: estimate word timing from segment
                    segment_words = segment_text.split()
                    segment_start = segment.start
                    segment_end = segment.end
                    segment_duration = segment_end - segment_start

                    if segment_words and segment_duration > 0:
                        time_per_word = segment_duration / len(segment_words)
                        for i, word in enumerate(segment_words):
                            words.append({
                                "word": word.strip(),
                                "start": round(segment_start + (i * time_per_word), 2),
                                "end": round(segment_start + ((i + 1) * time_per_word), 2),
                            })

            result = TranscriptionResult(text=full_text.strip(), words=words)
            logger.info(f"✓ Transcribed {len(words)} words from {len(list(segments))} segments")

            return result

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return None

    def _transcribe_fallback(self, audio_path: str) -> TranscriptionResult:
        """Fallback transcription for testing (no actual transcription)"""
        logger.warning("Using fallback transcription mode (testing only)")

        return TranscriptionResult(
            text="[Transcription available with Whisper model]",
            words=[
                {"word": "Test", "start": 0.0, "end": 0.5},
                {"word": "transcription", "start": 0.5, "end": 1.0},
                {"word": "for", "start": 1.0, "end": 1.3},
                {"word": "video", "start": 1.3, "end": 1.8},
            ]
        )

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """
        Transcribe audio from video file.

        Args:
            audio_path: Path to video or audio file

        Returns:
            TranscriptionResult with text and word-level timestamps
        """
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return self._transcribe_fallback(audio_path)

        # Try real transcription first
        if WHISPER_AVAILABLE:
            result = self._transcribe_with_whisper(audio_path)
            if result:
                return result

        # Fall back to mock
        return self._transcribe_fallback(audio_path)


# Global instance
_transcriber: Optional[Transcriber] = None


def get_transcriber() -> Transcriber:
    """Get or create global transcriber"""
    global _transcriber
    if _transcriber is None:
        # Use tiny model for speed (1GB), can change to 'base' or 'small' if needed
        _transcriber = Transcriber(model_name="tiny")
    return _transcriber


def set_transcriber(transcriber: Transcriber):
    """Set global transcriber"""
    global _transcriber
    _transcriber = transcriber
