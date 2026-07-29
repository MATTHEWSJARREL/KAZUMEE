"""
Unified Event Bus using Redis Streams for pub/sub and PostgreSQL for durability.

Architecture:
- Ingestion adapters emit StreamEvent to Redis Streams
- Consumer groups subscribe to specific event types
- Events are written to PostgreSQL for post-stream analysis
- Per-streamer channels isolate event volume (stream:{streamer_id}:events)
"""

import json
import redis.asyncio as aioredis
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
import os

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """All possible event types in the system"""
    # Chat/Community events
    CHAT_MESSAGE = "chat_message"
    FOLLOW = "follow"
    SUBSCRIBE = "subscribe"
    RAID = "raid"
    CHEER = "cheer"

    # Viewer metrics
    VIEWER_COUNT = "viewer_count"
    VIEWER_JOIN = "viewer_join"
    VIEWER_LEAVE = "viewer_leave"

    # Technical events
    AUDIO_PEAK = "audio_peak"
    QUALITY_DROP = "quality_drop"
    FRAME_DROP = "frame_drop"
    BITRATE_CHANGE = "bitrate_change"

    # Scene/OBS events
    SCENE_CHANGE = "scene_change"
    SOURCE_CHANGE = "source_change"
    RECORDING_START = "recording_start"
    RECORDING_STOP = "recording_stop"

    # Moment detection (AI-derived)
    MOMENT_DETECTED = "moment_detected"
    CLIP_GENERATED = "clip_generated"
    CLIP_PUBLISHED = "clip_published"

    # Health/System
    STREAM_HEALTH = "stream_health"
    ALERT_TRIGGERED = "alert_triggered"
    SYSTEM_ERROR = "system_error"


class Platform(str, Enum):
    """Streaming platforms supported"""
    TWITCH = "twitch"
    YOUTUBE = "youtube"
    KICK = "kick"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    OBS = "obs"
    SYSTEM = "system"


class StreamEvent(BaseModel):
    """Unified event schema - every event in the system conforms to this"""

    event_id: str                          # Unique ID for deduplication
    platform: Platform                     # Which platform this event came from
    event_type: EventType                  # What kind of event
    streamer_id: int                       # Which streamer this is for
    payload: Dict[str, Any]                # Platform-specific data
    raw: Optional[Dict[str, Any]] = None   # Original platform payload (for debugging)
    timestamp: datetime = None             # When it happened
    confidence: float = 1.0                # For AI-derived events (0-1 scale)

    class Config:
        use_enum_values = False

    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)

    def to_redis_format(self) -> str:
        """Convert to JSON for Redis storage"""
        return json.dumps({
            'event_id': self.event_id,
            'platform': self.platform.value,
            'event_type': self.event_type.value,
            'streamer_id': self.streamer_id,
            'payload': self.payload,
            'raw': self.raw,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
        })

    @staticmethod
    def from_redis_format(data: str) -> 'StreamEvent':
        """Parse from Redis JSON"""
        parsed = json.loads(data)
        parsed['timestamp'] = datetime.fromisoformat(parsed['timestamp'])
        parsed['platform'] = Platform(parsed['platform'])
        parsed['event_type'] = EventType(parsed['event_type'])
        return StreamEvent(**parsed)


class EventBus:
    """Central event bus using Redis Streams"""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis: Optional[aioredis.Redis] = None
        self.subscribers: Dict[str, List[Callable]] = {}

    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            # Test connection
            await self.redis.ping()
            logger.info(f"✓ Event Bus connected to {self.redis_url}")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            raise

    async def close(self):
        """Cleanup Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("✓ Event Bus connection closed")

    def _get_channel_name(self, streamer_id: int) -> str:
        """Per-streamer channel isolation"""
        return f"stream:{streamer_id}:events"

    async def publish(self, event: StreamEvent) -> str:
        """Publish event to Redis Stream for this streamer"""
        if not self.redis:
            raise RuntimeError("Event bus not connected. Call connect() first.")

        channel = self._get_channel_name(event.streamer_id)

        try:
            # Publish to Redis Stream (returns the message ID)
            message_id = await self.redis.xadd(
                channel,
                {'data': event.to_redis_format()}
            )
            logger.debug(f"Published event to {channel}: {event.event_type.value}")
            return message_id.decode() if isinstance(message_id, bytes) else message_id
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    async def subscribe(self, event_type: EventType, callback: Callable, name: str = None):
        """
        Subscribe to events of a specific type.
        Callback will be called with (event: StreamEvent) when event occurs.
        """
        key = f"{event_type.value}_{name or 'default'}"
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(callback)
        logger.debug(f"Registered subscriber for {event_type.value}: {name}")

    async def get_events(
        self,
        streamer_id: int,
        since: Optional[datetime] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[StreamEvent]:
        """
        Query events from a specific time range.
        Used for post-stream report generation.
        """
        if not self.redis:
            raise RuntimeError("Event bus not connected.")

        channel = self._get_channel_name(streamer_id)

        try:
            # Get all events from stream
            messages = await self.redis.xread({channel: '0'}, count=limit)

            events = []
            if messages:
                for _, message_list in messages:
                    for msg_id, data in message_list:
                        try:
                            event = StreamEvent.from_redis_format(data[b'data'].decode())

                            # Filter by time if specified
                            if since and event.timestamp < since:
                                continue

                            # Filter by event type if specified
                            if event_type and event.event_type != event_type:
                                continue

                            events.append(event)
                        except Exception as e:
                            logger.warning(f"Failed to parse event: {e}")
                            continue

            return events
        except Exception as e:
            logger.error(f"Failed to query events: {e}")
            raise


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def init_event_bus(redis_url: Optional[str] = None) -> EventBus:
    """Initialize the global event bus"""
    global _event_bus
    _event_bus = EventBus(redis_url)
    await _event_bus.connect()
    return _event_bus
