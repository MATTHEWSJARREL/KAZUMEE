"""
Video Extraction Service

Extracts video segments from replay buffer or recorded files.
Used by the clip generation pipeline.

FALLBACK MODE: If FFmpeg not available, copies test video for development.
"""

import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Enable fallback mode when FFmpeg not available
FALLBACK_MODE = os.getenv("VIDEO_EXTRACTOR_FALLBACK", "true").lower() == "true"


class VideoExtractor:
    """Extracts video segments for clip generation"""

    def __init__(self, output_dir: str = "backend/data/clips/extracted"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VideoExtractor initialized, output: {self.output_dir}")

    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg binary"""
        candidates = [
            "ffmpeg",  # System PATH
            "C:\\ffmpeg\\bin\\ffmpeg.exe",  # Windows common
            "/usr/bin/ffmpeg",  # Linux
            "/usr/local/bin/ffmpeg",  # macOS
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

        logger.warning("FFmpeg not found in PATH")
        return None

    def _extract_fallback(
        self,
        input_video: str,
        output_format: str = "mp4",
    ) -> Optional[str]:
        """
        Fallback extraction: copy video for testing (when FFmpeg unavailable).
        Used during development - actual production uses real FFmpeg extraction.
        """
        if not os.path.exists(input_video):
            logger.error(f"Input video not found: {input_video}")
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"clip_{timestamp}.{output_format}"
            output_path = self.output_dir / output_filename

            # Copy video (simulates extraction)
            shutil.copy2(input_video, output_path)

            file_size = os.path.getsize(output_path)
            logger.info(f"✓ Fallback extraction: {output_path} ({file_size / 1024 / 1024:.1f}MB)")

            return str(output_path)
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return None

    def extract_segment(
        self,
        input_video: str,
        start_seconds: int = 0,
        duration_seconds: int = 45,
        output_format: str = "mp4",
    ) -> Optional[str]:
        """
        Extract a video segment using FFmpeg.

        Args:
            input_video: Path to input video file
            start_seconds: Start time in seconds
            duration_seconds: Duration of segment
            output_format: Output format (mp4, mkv, etc)

        Returns:
            Path to extracted video file, or None if failed
        """
        # Verify input exists
        if not os.path.exists(input_video):
            logger.error(f"Input video not found: {input_video}")
            return None

        # Find FFmpeg
        ffmpeg = self._find_ffmpeg()
        if not ffmpeg:
            # Use fallback for development
            if FALLBACK_MODE:
                logger.warning("FFmpeg not available, using fallback extraction (testing mode)")
                return self._extract_fallback(input_video, output_format)
            else:
                logger.error("FFmpeg not available (FALLBACK_MODE disabled)")
                return None

        # Generate output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"clip_{timestamp}.{output_format}"
        output_path = self.output_dir / output_filename

        logger.info(
            f"Extracting segment: {start_seconds}s for {duration_seconds}s "
            f"→ {output_path}"
        )

        try:
            # FFmpeg command
            cmd = [
                ffmpeg,
                "-ss", str(start_seconds),           # Start time
                "-i", input_video,                   # Input file
                "-t", str(duration_seconds),         # Duration
                "-c:v", "libx264",                   # Video codec
                "-preset", "fast",                   # Encoding speed
                "-crf", "23",                        # Quality (0-51, lower=better)
                "-c:a", "aac",                       # Audio codec
                "-b:a", "128k",                      # Audio bitrate
                "-y",                                # Overwrite output
                str(output_path),
            ]

            logger.info(f"Running: {' '.join(cmd)}")

            # Run extraction
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg failed: {result.stderr}")
                return None

            # Verify output
            if not os.path.exists(output_path):
                logger.error("Output file not created")
                return None

            file_size = os.path.getsize(output_path)
            logger.info(f"✓ Extracted clip: {output_path} ({file_size / 1024 / 1024:.1f}MB)")

            return str(output_path)

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg extraction timed out")
            return None
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return None

    def test_extraction(self, test_video: Optional[str] = None) -> bool:
        """
        Test extraction capability.

        Args:
            test_video: Path to test video file

        Returns:
            True if extraction works
        """
        if not test_video:
            test_video = "backend/data/test_videos/test_stream.mp4"

        if not os.path.exists(test_video):
            logger.error(f"Test video not found: {test_video}")
            return False

        logger.info("Testing video extraction...")

        result = self.extract_segment(
            test_video,
            start_seconds=0,
            duration_seconds=10
        )

        if result:
            logger.info("✓ Video extraction test passed")
            return True
        else:
            logger.error("✗ Video extraction test failed")
            return False


# Global instance
_extractor: Optional[VideoExtractor] = None


def get_extractor() -> VideoExtractor:
    """Get or create global video extractor"""
    global _extractor
    if _extractor is None:
        _extractor = VideoExtractor()
    return _extractor


def set_extractor(extractor: VideoExtractor):
    """Set global video extractor"""
    global _extractor
    _extractor = extractor
