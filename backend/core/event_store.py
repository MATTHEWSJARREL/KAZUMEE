import hashlib
import json
from typing import Optional

from backend.database.models.stream_event import StreamEvent


def _hash_payload(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def insert_stream_event(
    db,
    streamer_id: int,
    platform: str,
    event_type: str,
    event_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    message: Optional[str] = None,
    payload: Optional[dict] = None,
) -> bool:
    dedupe_id = event_id
    if not dedupe_id and payload:
        dedupe_id = _hash_payload(payload)

    if dedupe_id:
        exists = (
            db.query(StreamEvent)
            .filter(
                StreamEvent.streamer_id == streamer_id,
                StreamEvent.platform == platform,
                StreamEvent.event_id == dedupe_id,
            )
            .first()
        )
        if exists:
            return False

    event = StreamEvent(
        streamer_id=streamer_id,
        platform=platform,
        event_type=event_type,
        event_id=dedupe_id,
        user_id=user_id,
        username=username,
        message=message,
        payload=payload,
    )
    db.add(event)
    return True
