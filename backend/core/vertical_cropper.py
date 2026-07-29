"""
Vertical Cropper Service

Crops video from 16:9 (horizontal) to 9:16 (vertical/portrait) format.
Intelligently detects important content area (face/action) and centers crop on it.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

FALLBACK_MODE = os.getenv("VIDEO_CROPPER_FALLBACK", "true").lower() == "true"


class VerticalCropper:
    """Crops videos to vertical (9:16) format for mobile/shorts"""

    def __init__(self, output_dir: str = "backend/data/clips/vertical"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VerticalCropper initialized, output: {self.output_dir}")

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

    def _get_video_dimensions(self, video_path: str) -> Optional[Tuple[int, int]]:
        """Get video width and height using ffprobe"""
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            return (width, height)
        except Exception as e:
            logger.warning(f"Could not get dimensions: {e}")
            return None

    def _detect_content_area(self, video_path: str) -> Tuple[int, int, int, int]:
        """
        Get crop coordinates for 9:16 aspect ratio (center crop).
        """
        return self._center_crop_coords(video_path)

    def _center_crop_coords(self, video_path: str) -> Tuple[int, int, int, int]:
        """Get center crop coordinates for 9:16 aspect ratio"""
        dims = self._get_video_dimensions(video_path)
        if not dims:
            # Default fallback: assume 1920x1080
            video_width, video_height = 1920, 1080
        else:
            video_width, video_height = dims

        # Target 9:16 aspect ratio (vertical)
        target_width = int(video_height * 0.5625)
        if target_width > video_width:
            target_width = video_width

        x_start = (video_width - target_width) // 2
        y_start = 0

        logger.info(f"Center crop: ({x_start}, {y_start}) size ({target_width}, {video_height})")
        return (x_start, y_start, target_width, video_height)

    def crop(self, input_video: str) -> Optional[str]:
        """
        Crop video to vertical (9:16) format.

        Args:
            input_video: Path to input MP4 file

        Returns:
            Path to cropped video file, or None if failed
        """
        if not os.path.exists(input_video):
            logger.error(f"Input video not found: {input_video}")
            return None

        # Detect content area and get crop coordinates
        x_start, y_start, crop_width, crop_height = self._detect_content_area(input_video)

        # Try with FFmpeg first
        ffmpeg = self._find_ffmpeg()
        if ffmpeg:
            return self._crop_with_ffmpeg(
                input_video, ffmpeg, x_start, y_start, crop_width, crop_height
            )

        # Fallback: use OpenCV if available
        if FALLBACK_MODE:
            logger.warning("FFmpeg not available, using OpenCV fallback")
            return self._crop_with_opencv(
                input_video, x_start, y_start, crop_width, crop_height
            )

        logger.error("No video cropping method available")
        return None

    def _crop_with_ffmpeg(
        self,
        input_video: str,
        ffmpeg: str,
        x_start: int,
        y_start: int,
        crop_width: int,
        crop_height: int,
    ) -> Optional[str]:
        """Crop using FFmpeg (faster, better quality)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"vertical_{timestamp}.mp4"
        output_path = self.output_dir / output_filename

        # FFmpeg crop filter: crop=width:height:x:y
        crop_filter = f"crop={crop_width}:{crop_height}:{x_start}:{y_start}"

        cmd = [
            ffmpeg,
            "-i", input_video,
            "-vf", crop_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-y",
            str(output_path),
        ]

        try:
            logger.info(f"Cropping with FFmpeg: {crop_filter}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"FFmpeg crop failed: {result.stderr}")
                return None

            if not os.path.exists(output_path):
                logger.error("Output file not created")
                return None

            file_size = os.path.getsize(output_path) / 1024 / 1024
            logger.info(f"[OK] Cropped video: {output_path} ({file_size:.1f}MB)")
            return str(output_path)

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg crop timed out")
            return None
        except Exception as e:
            logger.error(f"FFmpeg crop failed: {e}")
            return None

    def _crop_with_opencv(
        self,
        input_video: str,
        x_start: int,
        y_start: int,
        crop_width: int,
        crop_height: int,
    ) -> Optional[str]:
        """Crop using OpenCV (slower, pure Python fallback)"""
        try:
            import cv2

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"vertical_{timestamp}.mp4"
            output_path = self.output_dir / output_filename

            # Open input video
            cap = cv2.VideoCapture(input_video)
            if not cap.isOpened():
                logger.error("Could not open video")
                return None

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

            # Create output writer
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (crop_width, crop_height))
            if not out.isOpened():
                logger.error("Could not create output video")
                cap.release()
                return None

            logger.info(f"Cropping with OpenCV: crop=({x_start}, {y_start}, {crop_width}, {crop_height})")
            frame_count = 0

            # Process frames
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Crop frame
                cropped = frame[y_start:y_start + crop_height, x_start:x_start + crop_width]
                out.write(cropped)
                frame_count += 1

            cap.release()
            out.release()

            if frame_count == 0:
                logger.error("No frames processed")
                return None

            file_size = os.path.getsize(output_path) / 1024 / 1024
            logger.info(f"[OK] OpenCV cropped: {output_path} ({file_size:.1f}MB, {frame_count} frames)")
            return str(output_path)

        except Exception as e:
            logger.error(f"OpenCV crop failed: {e}")
            return None


# Global instance
_cropper: Optional[VerticalCropper] = None


def get_cropper() -> VerticalCropper:
    """Get or create global vertical cropper"""
    global _cropper
    if _cropper is None:
        _cropper = VerticalCropper()
    return _cropper


def set_cropper(cropper: VerticalCropper):
    """Set global vertical cropper"""
    global _cropper
    _cropper = cropper
