import logging
import json
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pathlib import Path
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# Logging configuration
LOG_DIR = Path("backend/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create specialized loggers
logger = logging.getLogger("app")
clip_logger = logging.getLogger("clips")
api_logger = logging.getLogger("api")
error_logger = logging.getLogger("errors")

# Configure file handlers
clips_handler = logging.FileHandler(LOG_DIR / "clips.log")
clips_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
clip_logger.addHandler(clips_handler)
clip_logger.setLevel(logging.INFO)

api_handler = logging.FileHandler(LOG_DIR / "api.log")
api_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
api_logger.addHandler(api_handler)
api_logger.setLevel(logging.INFO)

error_handler = logging.FileHandler(LOG_DIR / "errors.log")
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.ERROR)


def get_logger(name: str):
    return logging.getLogger(name)


class EventType(str, Enum):
    """Types of events to track"""
    CLIP_DETECTED = "clip_detected"
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_SUCCEEDED = "extraction_succeeded"
    EXTRACTION_FAILED = "extraction_failed"
    CLIP_APPROVED = "clip_approved"
    CLIP_REJECTED = "clip_rejected"
    CLIP_EXPORTED = "clip_exported"
    CLIP_DELETED = "clip_deleted"
    API_REQUEST = "api_request"
    API_ERROR = "api_error"
    AUTH_FAILURE = "auth_failure"
    STORAGE_ERROR = "storage_error"


class Event:
    """Structured event for monitoring"""

    def __init__(
        self,
        event_type: EventType,
        streamer_id: str,
        message: str,
        clip_id: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_type = event_type.value
        self.streamer_id = streamer_id
        self.clip_id = clip_id
        self.message = message
        self.duration_ms = duration_ms
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "type": self.event_type,
            "streamer_id": self.streamer_id,
            "clip_id": self.clip_id,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class EventLog:
    """In-memory event log for recent events"""

    def __init__(self, max_events: int = 1000):
        self.events: list[Event] = []
        self.max_events = max_events
        self.error_count = 0
        self.success_count = 0

    def log_event(self, event: Event):
        self.events.append(event)

        # Track success/error counts
        if "succeeded" in event.event_type or "approved" in event.event_type or "exported" in event.event_type:
            self.success_count += 1
        elif "failed" in event.event_type or "rejected" in event.event_type or "error" in event.event_type:
            self.error_count += 1

        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        # Write to appropriate logger
        if event.error:
            error_logger.error(f"{event.event_type}: {event.message} - {event.error}")
        else:
            if "extraction" in event.event_type or "clip" in event.event_type:
                clip_logger.info(f"{event.event_type}: {event.message}")
            else:
                api_logger.info(f"{event.event_type}: {event.message}")

    def get_recent_events(self, limit: int = 50, event_type: Optional[str] = None) -> list[Dict]:
        filtered = self.events
        if event_type:
            filtered = [e for e in filtered if event_type in e.event_type]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_errors(self, limit: int = 50) -> list[Dict]:
        errors = [e for e in self.events if e.error or "error" in e.event_type or "failed" in e.event_type]
        return [e.to_dict() for e in errors[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total = self.success_count + self.error_count
        return {
            "total_events": len(self.events),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": round((self.success_count / total * 100) if total > 0 else 0, 2),
            "last_event": self.events[-1].to_dict() if self.events else None
        }


# Global event log
_event_log = EventLog()


def get_event_log() -> EventLog:
    return _event_log


def log_event(
    event_type: EventType,
    streamer_id: str,
    message: str,
    clip_id: Optional[int] = None,
    duration_ms: Optional[int] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    event = Event(event_type, streamer_id, message, clip_id, duration_ms, error, metadata)
    _event_log.log_event(event)
