"""
Clip Storage Service

Handles clip file storage, retrieval, and streaming.
Supports both local storage (default) and S3 (future).
"""

import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Storage configuration
CLIPS_DIR = Path("backend/data/clips")
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

EXTRACTED_CLIPS_DIR = CLIPS_DIR / "extracted"
EXTRACTED_CLIPS_DIR.mkdir(parents=True, exist_ok=True)

APPROVED_CLIPS_DIR = CLIPS_DIR / "approved"
APPROVED_CLIPS_DIR.mkdir(parents=True, exist_ok=True)

EXPORTED_CLIPS_DIR = CLIPS_DIR / "exported"
EXPORTED_CLIPS_DIR.mkdir(parents=True, exist_ok=True)


class ClipStorage:
    """Local file storage for clips"""

    def __init__(self):
        self.clips_dir = CLIPS_DIR
        self.extracted_dir = EXTRACTED_CLIPS_DIR
        self.approved_dir = APPROVED_CLIPS_DIR
        self.exported_dir = EXPORTED_CLIPS_DIR
        logger.info(f"ClipStorage initialized: {self.clips_dir}")

    def get_clip_path(self, clip_id: int, file_path: str) -> Optional[Path]:
        """
        Get full path to a clip file.

        Args:
            clip_id: Clip database ID
            file_path: Stored file path from DB

        Returns:
            Full path if file exists, None otherwise
        """
        # If file_path is absolute, use it directly
        if os.path.isabs(file_path):
            path = Path(file_path)
        else:
            # Otherwise resolve relative to clips dir
            path = self.clips_dir / file_path

        if path.exists() and path.is_file():
            return path

        return None

    def get_clip_info(self, clip_id: int, file_path: str) -> Optional[dict]:
        """Get clip file info (size, modified time, etc)"""
        path = self.get_clip_path(clip_id, file_path)
        if not path:
            return None

        try:
            stat = path.stat()
            return {
                "path": str(path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "exists": True,
            }
        except Exception as e:
            logger.error(f"Failed to get clip info {clip_id}: {e}")
            return None

    def verify_clip_exists(self, file_path: str) -> bool:
        """Check if clip file exists"""
        if not file_path:
            return False

        # Handle both absolute and relative paths
        if os.path.isabs(file_path):
            return os.path.exists(file_path)

        # Try relative to clips dir
        full_path = self.clips_dir / file_path
        return full_path.exists()

    def get_clip_size(self, file_path: str) -> int:
        """Get clip file size in bytes"""
        if os.path.isabs(file_path):
            path = Path(file_path)
        else:
            path = self.clips_dir / file_path

        if path.exists():
            return path.stat().st_size
        return 0

    def delete_clip_file(self, file_path: str) -> bool:
        """Delete a clip file from storage"""
        try:
            if os.path.isabs(file_path):
                path = Path(file_path)
            else:
                path = self.clips_dir / file_path

            if path.exists():
                path.unlink()
                logger.info(f"Deleted clip: {path}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete clip {file_path}: {e}")
        return False

    def move_clip(self, src_path: str, dst_dir: Path) -> Optional[str]:
        """
        Move a clip from one directory to another.

        Args:
            src_path: Source file path
            dst_dir: Destination directory

        Returns:
            New relative path, or None if failed
        """
        try:
            if os.path.isabs(src_path):
                src = Path(src_path)
            else:
                src = self.clips_dir / src_path

            if not src.exists():
                logger.error(f"Source clip not found: {src}")
                return None

            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / src.name

            # Move file
            src.rename(dst)
            logger.info(f"Moved clip: {src} → {dst}")

            # Return path relative to clips_dir
            return str(dst.relative_to(self.clips_dir))
        except Exception as e:
            logger.error(f"Failed to move clip: {e}")
            return None

    def get_storage_stats(self) -> dict:
        """Get storage usage statistics"""
        total_size = 0
        total_files = 0

        for root, dirs, files in os.walk(self.clips_dir):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(filepath)
                    total_files += 1
                except OSError:
                    pass

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "extracted_files": len(list(self.extracted_dir.glob("*.mp4"))),
            "approved_files": len(list(self.approved_dir.glob("*.mp4"))),
            "exported_files": len(list(self.exported_dir.glob("*.mp4"))),
        }


# Global instance
_storage: Optional[ClipStorage] = None


def get_clip_storage() -> ClipStorage:
    """Get or create global clip storage instance"""
    global _storage
    if _storage is None:
        _storage = ClipStorage()
    return _storage


def set_clip_storage(storage: ClipStorage):
    """Set global clip storage instance"""
    global _storage
    _storage = storage
