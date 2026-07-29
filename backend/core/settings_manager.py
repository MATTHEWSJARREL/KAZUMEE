"""
Streamer Settings Manager

Manages detection sensitivity, auto-publish, and other per-streamer settings.
Integrates with MomentDetector to control behavior in real-time.
"""

import json
import logging
from typing import Optional, Dict, Any

from backend.database.session import SessionLocal
from backend.database.models.streamer import Streamer

logger = logging.getLogger(__name__)


class StreamerSettings:
    """Per-streamer configuration"""

    def __init__(self):
        # Moment Detection Settings
        self.sensitivity: float = 0.7  # 0.0-1.0, default 0.7 (balanced)
        self.min_quality_score: float = 0.3  # Minimum quality for auto-clip (0.0-1.0)

        # Auto-Publish Settings
        self.auto_publish: bool = False
        self.auto_publish_platforms: list = []  # ["tiktok", "shorts", "reels"]

        # Notification Settings
        self.notify_on_clip: bool = True
        self.notify_on_publish: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            "sensitivity": self.sensitivity,
            "min_quality_score": self.min_quality_score,
            "auto_publish": self.auto_publish,
            "auto_publish_platforms": self.auto_publish_platforms,
            "notify_on_clip": self.notify_on_clip,
            "notify_on_publish": self.notify_on_publish,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamerSettings":
        """Create from dict"""
        settings = cls()
        if data:
            settings.sensitivity = float(data.get("sensitivity", 0.7))
            settings.min_quality_score = float(data.get("min_quality_score", 0.3))
            settings.auto_publish = bool(data.get("auto_publish", False))
            settings.auto_publish_platforms = data.get("auto_publish_platforms", [])
            settings.notify_on_clip = bool(data.get("notify_on_clip", True))
            settings.notify_on_publish = bool(data.get("notify_on_publish", True))
        return settings


class SettingsManager:
    """Loads and manages streamer settings from database"""

    def __init__(self):
        self._cache: Dict[int, StreamerSettings] = {}
        logger.info("Settings Manager initialized")

    def get_settings(self, streamer_id: int, force_refresh: bool = False) -> StreamerSettings:
        """Get settings for a streamer (cached)"""
        if not force_refresh and streamer_id in self._cache:
            return self._cache[streamer_id]

        db = SessionLocal()
        try:
            streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
            if not streamer:
                settings = StreamerSettings()
            else:
                # Load from database
                settings_data = streamer.settings_json or {}
                if isinstance(settings_data, str):
                    settings_data = json.loads(settings_data)
                settings = StreamerSettings.from_dict(settings_data)

            self._cache[streamer_id] = settings
            return settings
        except Exception as e:
            logger.error(f"Failed to load settings for streamer {streamer_id}: {e}")
            return StreamerSettings()  # Return defaults on error
        finally:
            db.close()

    def save_settings(self, streamer_id: int, settings: StreamerSettings) -> bool:
        """Save settings to database"""
        db = SessionLocal()
        try:
            streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
            if not streamer:
                logger.error(f"Streamer {streamer_id} not found")
                return False

            streamer.settings_json = json.dumps(settings.to_dict())
            db.commit()

            # Invalidate cache
            if streamer_id in self._cache:
                del self._cache[streamer_id]

            logger.info(f"Saved settings for streamer {streamer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings for streamer {streamer_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def update_sensitivity(self, streamer_id: int, sensitivity: float) -> bool:
        """Update detection sensitivity (0.0-1.0)"""
        settings = self.get_settings(streamer_id)
        settings.sensitivity = max(0.0, min(1.0, float(sensitivity)))
        return self.save_settings(streamer_id, settings)

    def clear_cache(self, streamer_id: Optional[int] = None):
        """Clear cache entry or all"""
        if streamer_id:
            self._cache.pop(streamer_id, None)
        else:
            self._cache.clear()


# Global settings manager instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get or create global settings manager"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def set_settings_manager(manager: SettingsManager):
    """Set global settings manager"""
    global _settings_manager
    _settings_manager = manager
