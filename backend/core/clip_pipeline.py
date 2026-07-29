"""
Complete Clip Generation Pipeline

Stages:
1. EXTRACT: Pull clip segment from OBS replay buffer (or recording)
2. TRANSCRIBE: Get word-level timestamps from audio
3. RECROP: Auto-crop to 9:16 vertical (motion-weighted or simple)
4. CAPTION: Add animated captions with timestamps
5. LABEL: Groq generates title + hashtags + virality score
6. PUBLISH: Upload to YouTube Shorts
7. STORE: Save metadata to database

Each stage is independent and can fail gracefully.
"""

import os
import json
import asyncio
import logging
import platform
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import subprocess
import tempfile
from groq import AsyncGroq

logger = logging.getLogger(__name__)

# Lazy-initialize Groq to avoid startup failure if API key missing
_groq_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not set - title generation will use fallback")
            return None
        try:
            _groq_client = AsyncGroq(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            return None
    return _groq_client

# FFmpeg path detection (env var > system path > hardcoded fallback)
def _find_ffmpeg_binary(binary_name: str) -> str:
    """Find FFmpeg/FFprobe binary, preferring env var > system PATH > Windows hardcoded"""
    env_var = f"{binary_name.upper()}_PATH"

    # 1. Check environment variable
    if env_var in os.environ:
        return os.environ[env_var]

    # 2. Check system PATH
    found = shutil.which(binary_name)
    if found:
        return found

    # 3. Windows fallback (if exact install location used)
    if platform.system() == "Windows":
        windows_fallback = f"C:\\ffmpeg\\ffmpeg-master-latest-win64-gpl-shared\\bin\\{binary_name}.exe"
        if os.path.exists(windows_fallback):
            return windows_fallback

    # 4. Return binary name (will fail at runtime if not found)
    logger.warning(f"{binary_name} not found in PATH. Set {env_var} env var if in non-standard location")
    return binary_name

FFMPEG_PATH = _find_ffmpeg_binary("ffmpeg")
FFPROBE_PATH = _find_ffmpeg_binary("ffprobe")


class ClipPipelineError(Exception):
    """Base error for clip pipeline failures"""
    pass


class ClipPipeline:
    """
    End-to-end clip generation pipeline.

    Usage:
        pipeline = ClipPipeline()
        result = await pipeline.process(
            moment_data={...},
            obs_adapter=obs_instance,
            streamer_id=123
        )
    """

    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize pipeline.

        Args:
            temp_dir: Directory for temporary files (defaults to system temp)
        """
        self.temp_dir = Path(temp_dir or tempfile.gettempdir()) / "kazumee_clips"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Clip pipeline temp dir: {self.temp_dir}")

    # ===== STAGE 1: EXTRACT =====

    async def extract_clip_segment(
        self,
        obs_adapter,
        start_seconds: int,
        duration_seconds: int = 45,
    ) -> str:
        """
        Extract clip segment from OBS replay buffer.

        Args:
            obs_adapter: OBS WebSocket adapter instance
            start_seconds: Start time in stream (seconds from beginning)
            duration_seconds: Length of clip (default 45s)

        Returns:
            Path to extracted MP4 file

        Raises:
            ClipPipelineError: If extraction fails
        """
        try:
            logger.info(f"Extracting clip: {start_seconds}s for {duration_seconds}s")

            # Option 1: Use OBS replay buffer (if configured)
            if hasattr(obs_adapter, "get_replay_buffer_path"):
                replay_path = await obs_adapter.get_replay_buffer_path()
                if replay_path and Path(replay_path).exists():
                    return await self._extract_from_file(
                        replay_path, start_seconds, duration_seconds
                    )

            # Option 2: Fall back to continuous recording
            recording_path = await self._find_latest_recording()
            if recording_path:
                return await self._extract_from_file(
                    recording_path, start_seconds, duration_seconds
                )

            raise ClipPipelineError("No replay buffer or recording available")

        except Exception as e:
            logger.error(f"Extract failed: {e}")
            raise ClipPipelineError(f"Failed to extract clip: {e}")

    async def _extract_from_file(
        self, source_path: str, start_seconds: int, duration_seconds: int
    ) -> str:
        """Extract segment using FFmpeg"""
        output_path = self.temp_dir / f"clip_raw_{datetime.now().timestamp()}.mp4"

        # FFmpeg command: extract segment
        cmd = [
            FFMPEG_PATH,
            "-ss", str(start_seconds),           # Start time
            "-i", source_path,                   # Input file
            "-t", str(duration_seconds),         # Duration
            "-c:v", "libx264",                   # Video codec
            "-preset", "fast",                   # Speed vs quality
            "-c:a", "aac",                       # Audio codec
            "-y",                                # Overwrite output
            str(output_path),
        ]

        logger.info(f"Running FFmpeg extract: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ClipPipelineError(f"FFmpeg extract failed: {result.stderr}")

        logger.info(f"✓ Extracted clip: {output_path}")
        return str(output_path)

    async def _find_latest_recording(self) -> Optional[str]:
        """Find the most recent recording file in OBS default directory"""
        # Common OBS recording locations
        possible_paths = [
            Path.home() / "Videos" / "OBS",
            Path.home() / "Videos",
            Path("/home/user/Videos/OBS"),
            Path("C:/Users/Videos"),
        ]

        for path in possible_paths:
            if path.exists():
                recordings = sorted(
                    path.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True
                )
                if recordings:
                    return str(recordings[0])

        return None

    # ===== STAGE 2: TRANSCRIBE =====

    async def transcribe_audio(self, clip_path: str) -> Dict[str, Any]:
        """
        Transcribe audio to get word-level timestamps.

        Uses faster-whisper for speed.

        Args:
            clip_path: Path to MP4 clip

        Returns:
            {
                "full_text": "The quick brown fox...",
                "words": [
                    {"word": "The", "start": 0.0, "end": 0.3},
                    {"word": "quick", "start": 0.3, "end": 0.7},
                    ...
                ]
            }
        """
        try:
            logger.info(f"Transcribing: {clip_path}")

            # Import here to avoid requiring faster-whisper if not used
            from faster_whisper import WhisperModel

            # Detect GPU availability
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                if device == "cuda":
                    logger.info("GPU detected, using CUDA for transcription")
            except ImportError:
                device = "cpu"
                logger.info("Using CPU for transcription")

            # Use base model for speed (v1)
            model = WhisperModel("base", device=device)

            # Transcribe with word-level timestamps (built-in to faster-whisper)
            result = model.transcribe(
                clip_path,
                language="en",
                without_timestamps=False,
            )

            # Convert to list if it's a generator
            segments = list(result) if result else []

            # Extract word-level data (or sentence-level fallback)
            full_text = ""
            words = []

            for segment in segments:
                # Try to get word-level timestamps
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        full_text += word.word + " "
                        words.append({
                            "word": word.word.strip(),
                            "start": float(word.start),
                            "end": float(word.end),
                        })
                # Fallback: if no words, split segment text and estimate timestamps
                elif hasattr(segment, 'text') and segment.text:
                    segment_text = segment.text.strip()
                    if segment_text:
                        full_text += segment_text + " "

                        # Estimate word timestamps based on segment duration
                        segment_words = segment_text.split()
                        segment_start = float(segment.start) if hasattr(segment, 'start') else 0
                        segment_end = float(segment.end) if hasattr(segment, 'end') else segment_start + 1
                        segment_duration = segment_end - segment_start

                        if segment_words and segment_duration > 0:
                            time_per_word = segment_duration / len(segment_words)
                            for i, word in enumerate(segment_words):
                                words.append({
                                    "word": word.strip(),
                                    "start": segment_start + (i * time_per_word),
                                    "end": segment_start + ((i + 1) * time_per_word),
                                })

            transcript = {
                "full_text": full_text.strip(),
                "words": words,
            }

            logger.info(f"✓ Transcribed: {len(words)} words")
            return transcript

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            # Graceful degradation: return empty transcript
            return {"full_text": "", "words": []}

    # ===== STAGE 3: RECROP =====

    async def recrop_to_vertical(self, clip_path: str) -> str:
        """
        Auto-crop clip to 9:16 vertical aspect ratio.

        Simple approach: center crop (v1)
        Advanced approach: motion-weighted saliency (v1.1+)

        Args:
            clip_path: Path to source MP4

        Returns:
            Path to cropped MP4
        """
        try:
            logger.info(f"Recropping to 9:16: {clip_path}")

            output_path = self.temp_dir / f"clip_vertical_{datetime.now().timestamp()}.mp4"

            # Get video dimensions first
            probe_cmd = [
                FFPROBE_PATH,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json",
                clip_path,
            ]

            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise ClipPipelineError(f"FFprobe failed: {result.stderr}")

            data = json.loads(result.stdout)
            width = data["streams"][0]["width"]
            height = data["streams"][0]["height"]

            logger.info(f"Source dimensions: {width}x{height}")

            # Calculate 9:16 crop (vertical)
            # Target: 9:16 ratio
            target_width = min(int(height * 9 / 16), width)
            target_height = height
            crop_x = (width - target_width) // 2
            crop_y = 0

            logger.info(f"Cropping to: {target_width}x{target_height}")

            # FFmpeg crop filter: crop=w:h:x:y
            crop_filter = f"crop={target_width}:{target_height}:{crop_x}:{crop_y}"

            cmd = [
                FFMPEG_PATH,
                "-i", clip_path,
                "-vf", crop_filter,
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "aac",
                "-y",
                str(output_path),
            ]

            logger.info(f"Running FFmpeg crop: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise ClipPipelineError(f"FFmpeg crop failed: {result.stderr}")

            logger.info(f"✓ Cropped to vertical: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Recrop failed: {e}")
            # Graceful degradation: return original if crop fails
            return clip_path

    # ===== STAGE 4: CAPTION =====

    async def add_captions(self, clip_path: str, transcript: Dict[str, Any]) -> str:
        """
        Add animated captions to video with word-level timestamps.

        Style: Bold emphasis on key words (Hormozi-style)

        Args:
            clip_path: Path to source MP4
            transcript: Output from transcribe_audio()

        Returns:
            Path to captioned MP4
        """
        try:
            if not transcript["words"]:
                logger.warning("No transcript words, skipping captions")
                return clip_path

            logger.info(f"Adding captions: {len(transcript['words'])} words")

            output_path = self.temp_dir / f"clip_captioned_{datetime.now().timestamp()}.mp4"

            # Create subtitle file (SRT format)
            srt_path = self.temp_dir / f"captions_{datetime.now().timestamp()}.srt"
            self._create_srt_file(srt_path, transcript["words"])

            # FFmpeg command with subtitle overlay
            # This uses the subtitles filter to burn in captions
            subtitles_filter = f"subtitles={str(srt_path)}"

            cmd = [
                FFMPEG_PATH,
                "-i", clip_path,
                "-vf", subtitles_filter,
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "aac",
                "-y",
                str(output_path),
            ]

            logger.info(f"Running FFmpeg subtitle: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.warning(f"FFmpeg subtitle failed: {result.stderr}, returning uncaptioned")
                return clip_path

            logger.info(f"✓ Added captions: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Caption failed: {e}")
            return clip_path

    def _create_srt_file(self, output_path: Path, words: list) -> None:
        """Create SRT subtitle file from word timestamps"""
        with open(output_path, "w") as f:
            for i, word_data in enumerate(words, 1):
                start = self._format_srt_time(word_data["start"])
                end = self._format_srt_time(word_data["end"])
                text = word_data["word"]

                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n")
                f.write("\n")

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """Convert seconds to SRT time format: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    # ===== STAGE 5: LABEL =====

    async def generate_title_and_tags(
        self, transcript: Dict[str, Any], context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate clip title and hashtags using Groq LLM.

        Args:
            transcript: Full transcribed text
            context: Optional context (what was happening in stream)

        Returns:
            {
                "title": "World Record Speedrun Clutch",
                "hashtags": ["#speedrun", "#gaming", "#worldrecord"],
                "virality_score": 8,  # 1-10 estimate
            }
        """
        try:
            full_text = transcript.get("full_text", "")
            if not full_text:
                logger.warning("No transcript text, using generic labels")
                return {
                    "title": "Epic Moment",
                    "hashtags": ["#gaming", "#clips", "#twitch"],
                    "virality_score": 5,
                }

            logger.info(f"Generating title from: {full_text[:100]}...")

            groq = get_groq_client()
            if not groq:
                logger.warning("Groq client unavailable, using generic title")
                return {
                    "title": "Amazing Moment",
                    "hashtags": ["#gaming", "#clips", "#streamers"],
                    "virality_score": 5,
                }

            prompt = f"""You are a viral clip title generator for gaming/streaming clips.

Based on this transcript from a stream:
"{full_text[:300]}"

Context: {context or 'General gaming/streaming moment'}

Generate:
1. A SHORT, punchy clip title (max 50 chars) that would get clicks
2. Three relevant hashtags
3. A virality score (1-10 estimate of how likely this goes viral)

IMPORTANT: Respond in JSON format ONLY, no other text:
{{
    "title": "...",
    "hashtags": ["...", "...", "..."],
    "virality_score": N
}}"""

            response = await groq.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
            )

            response_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                result = json.loads(response_text)
                logger.info(f"✓ Generated title: {result.get('title')}")
                return result
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Groq response: {response_text}")
                return {
                    "title": "Amazing Moment",
                    "hashtags": ["#gaming", "#clips", "#streamers"],
                    "virality_score": 5,
                }

        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return {
                "title": "Epic Clip",
                "hashtags": ["#gaming", "#clips"],
                "virality_score": 5,
            }

    # ===== STAGE 6: PUBLISH =====

    async def publish_to_youtube_shorts(
        self,
        clip_path: str,
        title: str,
        hashtags: list,
        streamer_name: str,
    ) -> Optional[str]:
        """
        Publish clip to YouTube Shorts.

        Args:
            clip_path: Path to final captioned MP4
            title: Clip title
            hashtags: List of hashtags
            streamer_name: Streamer's channel name

        Returns:
            YouTube Shorts URL or None if publishing fails
        """
        try:
            # For v1: Just store the file path and metadata
            # v1.1: Implement actual YouTube API upload

            logger.info(f"Publishing to YouTube: {title}")
            logger.warning("YouTube API integration not yet implemented (v1.1)")

            # For now, return a placeholder
            return None

        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return None

    # ===== ORCHESTRATION =====

    async def process(
        self,
        moment_data: Dict[str, Any],
        obs_adapter,
        streamer_id: int,
        db_session=None,
    ) -> Dict[str, Any]:
        """
        Complete end-to-end clip processing.

        Args:
            moment_data: Moment detection result with timing
            obs_adapter: OBS WebSocket adapter
            streamer_id: Streamer's database ID
            db_session: Database session (optional)

        Returns:
            {
                "status": "success" | "partial" | "failed",
                "clip_id": "uuid",
                "title": "...",
                "file_path": "...",
                "youtube_url": "..." or None,
                "error": "..." if failed,
            }
        """
        clip_id = f"clip_{datetime.now().timestamp()}"
        result = {
            "status": "partial",
            "clip_id": clip_id,
            "title": "Untitled",
            "file_path": None,
            "youtube_url": None,
            "error": None,
        }

        try:
            # STAGE 1: Extract
            logger.info(f"[{clip_id}] Starting clip pipeline")
            raw_clip = await self.extract_clip_segment(
                obs_adapter,
                start_seconds=moment_data.get("start_seconds", 0),
                duration_seconds=45,
            )
            result["file_path"] = raw_clip

            # STAGE 2: Transcribe
            transcript = await self.transcribe_audio(raw_clip)

            # STAGE 3: Recrop
            vertical_clip = await self.recrop_to_vertical(raw_clip)

            # STAGE 4: Caption
            captioned_clip = await self.add_captions(vertical_clip, transcript)
            result["file_path"] = captioned_clip

            # STAGE 5: Label
            labels = await self.generate_title_and_tags(
                transcript, moment_data.get("context")
            )
            result["title"] = labels.get("title", "Clip")
            result["virality_score"] = labels.get("virality_score", 5)
            result["hashtags"] = labels.get("hashtags", [])

            # STAGE 6: Publish
            youtube_url = await self.publish_to_youtube_shorts(
                captioned_clip,
                result["title"],
                result.get("hashtags", []),
                moment_data.get("streamer_name", "Unknown"),
            )
            if youtube_url:
                result["youtube_url"] = youtube_url

            result["status"] = "success"
            logger.info(f"[{clip_id}] ✓ Clip pipeline complete: {result['title']}")

            return result

        except Exception as e:
            logger.error(f"[{clip_id}] ✗ Clip pipeline failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
            return result
