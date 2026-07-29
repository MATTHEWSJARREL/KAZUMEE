"""
Caption Burner Service

Burns transcribed captions onto video frames with timing and styling.
"""

import logging
import os
import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class CaptionBurner:
    """Burns captions onto video files"""

    def __init__(self, output_dir: str = "backend/data/clips/captioned"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CaptionBurner initialized, output: {self.output_dir}")

    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg binary"""
        candidates = [
            "ffmpeg",
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ]
        for cmd in candidates:
            try:
                result = subprocess.run(
                    [cmd, "-version"],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    logger.info(f"Found FFmpeg: {cmd}")
                    return cmd
            except (FileNotFoundError, OSError):
                continue
        return None

    def _create_srt_subtitles(self, content_analysis: Dict) -> Optional[str]:
        """
        Create SRT subtitle file from transcription data.

        Args:
            content_analysis: Dict with 'words' list containing word timing info

        Returns:
            Path to .srt file, or None if failed
        """
        try:
            words = content_analysis.get("words", [])
            if not words:
                logger.warning("No words in content analysis")
                return None

            # Create SRT content
            srt_content = ""
            for i, word in enumerate(words, 1):
                start = self._seconds_to_srt_time(word.get("start", 0))
                end = self._seconds_to_srt_time(word.get("end", 0))
                text = word.get("word", "")

                srt_content += f"{i}\n{start} --> {end}\n{text}\n\n"

            # Save to temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            srt_path = self.output_dir / f"subtitles_{timestamp}.srt"

            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            logger.info(f"[OK] Created SRT file: {srt_path} with {len(words)} words")
            return str(srt_path)

        except Exception as e:
            logger.error(f"Failed to create SRT subtitles: {e}")
            return None

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        total_ms = int(seconds * 1000)
        hours = total_ms // 3600000
        minutes = (total_ms % 3600000) // 60000
        secs = (total_ms % 60000) // 1000
        ms = total_ms % 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    def burn_captions(self, video_path: str, content_analysis: Dict) -> Optional[str]:
        """
        Burn captions onto video.

        Args:
            video_path: Path to input video
            content_analysis: Dict with transcription and word timing

        Returns:
            Path to video with captions, or None if failed
        """
        if not os.path.exists(video_path):
            logger.error(f"Video not found: {video_path}")
            return None

        # Create SRT subtitle file
        srt_path = self._create_srt_subtitles(content_analysis)
        if not srt_path:
            logger.warning("Could not create subtitles, skipping caption burn")
            return None

        # Try with FFmpeg
        ffmpeg = self._find_ffmpeg()
        if ffmpeg:
            result = self._burn_with_ffmpeg(video_path, srt_path, ffmpeg)
            if result:
                return result

        # No fallback for captions - requires proper video processing
        logger.error("Could not burn captions: FFmpeg not available")
        return None

    def _burn_with_ffmpeg(self, video_path: str, srt_path: str, ffmpeg: str) -> Optional[str]:
        """Burn captions using FFmpeg and SRT file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"captioned_{timestamp}.mp4"
            output_path = self.output_dir / output_filename

            # Use FFmpeg with subtitles filter
            # Note: This requires the SRT file path in the filter
            srt_path_escaped = srt_path.replace("\\", "/").replace(":", r"\:")

            # Simple drawtext approach (writes one line of text)
            # For proper subtitle timing, would need to parse SRT and use complex filter graph
            cmd = [
                ffmpeg,
                "-i", video_path,
                "-vf",
                # Basic text overlay (just shows first subtitle)
                f"subtitles={srt_path_escaped}:force_style='FontName=Arial,FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2'",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-y",
                str(output_path),
            ]

            logger.info(f"Burning captions with FFmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"FFmpeg caption burn failed: {result.stderr}")
                return None

            if not os.path.exists(output_path):
                logger.error("Captioned output file not created")
                return None

            file_size = os.path.getsize(output_path) / 1024 / 1024
            logger.info(f"[OK] Captioned video: {output_path} ({file_size:.1f}MB)")
            return str(output_path)

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg caption burn timed out")
            return None
        except Exception as e:
            logger.error(f"Caption burn failed: {e}")
            return None


# Global instance
_burner: Optional[CaptionBurner] = None


def get_burner() -> CaptionBurner:
    """Get or create global caption burner"""
    global _burner
    if _burner is None:
        _burner = CaptionBurner()
    return _burner


def set_burner(burner: CaptionBurner):
    """Set global caption burner"""
    global _burner
    _burner = burner
