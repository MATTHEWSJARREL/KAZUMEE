import asyncio
import os
from datetime import datetime
import httpx
import logging
from sqlalchemy import func

from backend.database.session import SessionLocal
from backend.database.models.platform_connection import PlatformConnection
from backend.database.models.stream_event import StreamEvent
from backend.core.event_store import insert_stream_event
from backend.core.crypto import decrypt_token

logger = logging.getLogger(__name__)

YOUTUBE_POLL_INTERVAL = int(os.getenv("YOUTUBE_POLL_INTERVAL", "15"))
CHAT_POLLER_INTERVAL = int(os.getenv("CHAT_POLLER_INTERVAL", "2"))  # Poll stream_events every 2s

# Track last-processed stream_event ID per streamer (in-memory, survives process restart via DB scan)
_chat_poller_last_id: dict[int, int] = {}
_chat_poller_initialized = False


async def _initialize_chat_poller_markers() -> None:
	"""
	Initialize last-processed markers to skip pre-existing backlog on startup.
	Sets each streamer's marker to the current MAX stream_events id, so only
	NEW messages (arriving after startup) trigger the detector.
	"""
	global _chat_poller_last_id, _chat_poller_initialized
	if _chat_poller_initialized:
		return

	db = SessionLocal()
	try:
		# Get MAX id per streamer (only for chat_message events)
		max_ids = db.query(
			StreamEvent.streamer_id,
			func.max(StreamEvent.id).label('max_id')
		).filter(
			StreamEvent.event_type == "chat_message"
		).group_by(StreamEvent.streamer_id).all()

		for streamer_id, max_id in max_ids:
			if max_id:
				_chat_poller_last_id[streamer_id] = max_id
				logger.info(f"[CHAT→POLLER] Initialized streamer {streamer_id}: skipping to id {max_id}")

		_chat_poller_initialized = True
		logger.info(f"[CHAT→POLLER] Cold-start backlog skip enabled ({len(_chat_poller_last_id)} streamers)")
	finally:
		db.close()


async def poll_youtube_once(conn: PlatformConnection) -> None:
    meta = conn.meta or {}
    if meta.get("auto_poll") is False:
        return
    live_chat_id = meta.get("live_chat_id")
    if not live_chat_id:
        return

    headers = {"Authorization": f"Bearer {decrypt_token(conn.access_token)}"}
    params = {"liveChatId": live_chat_id, "part": "snippet,authorDetails"}
    next_token = meta.get("next_page_token")
    if next_token:
        params["pageToken"] = next_token
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://www.googleapis.com/youtube/v3/liveChat/messages",
            params=params,
            headers=headers,
        )
    if res.status_code >= 300:
        return
    data = res.json()
    items = data.get("items", [])

    db = SessionLocal()
    try:
        for item in items:
            snippet = item.get("snippet", {})
            author = item.get("authorDetails", {})
            insert_stream_event(
                db,
                streamer_id=conn.streamer_id,
                platform="youtube",
                event_type="chat_message",
                event_id=item.get("id"),
                user_id=author.get("channelId"),
                username=author.get("displayName"),
                message=snippet.get("displayMessage"),
                payload=item,
            )
        next_page = data.get("nextPageToken")
        if next_page:
            fresh = db.query(PlatformConnection).filter(PlatformConnection.id == conn.id).first()
            if fresh:
                fresh.meta = {**(fresh.meta or {}), "next_page_token": next_page, "last_polled_at": datetime.utcnow().isoformat()}
        db.commit()
    finally:
        db.close()


async def auto_subscribe_twitch(conn: PlatformConnection) -> None:
    meta = conn.meta or {}
    if meta.get("auto_subscribe") is False:
        return
    if meta.get("eventsub_subscribed"):
        return
    broadcaster_id = meta.get("broadcaster_id")
    webhook_url = meta.get("webhook_url") or os.getenv("TWITCH_WEBHOOK_URL")
    if not broadcaster_id or not webhook_url:
        return

    client_id = os.getenv("TWITCH_CLIENT_ID")
    secret = os.getenv("TWITCH_WEBHOOK_SECRET") or ""
    if not client_id:
        return

    headers = {
        "Authorization": f"Bearer {decrypt_token(conn.access_token)}",
        "Client-Id": client_id,
        "Content-Type": "application/json",
    }
    body = {
        "type": "channel.chat.message",
        "version": "1",
        "condition": {"broadcaster_user_id": broadcaster_id, "user_id": broadcaster_id},
        "transport": {"method": "webhook", "callback": f"{webhook_url}?streamer_id={conn.streamer_id}", "secret": secret},
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.twitch.tv/helix/eventsub/subscriptions",
            json=body,
            headers=headers,
        )
    if res.status_code >= 300:
        return

    db = SessionLocal()
    try:
        fresh = db.query(PlatformConnection).filter(PlatformConnection.id == conn.id).first()
        if fresh:
            fresh.meta = {**(fresh.meta or {}), "eventsub_subscribed": True, "eventsub_subscribed_at": datetime.utcnow().isoformat()}
            db.commit()
    finally:
        db.close()


async def poll_chat_events(stop_event: asyncio.Event) -> None:
    """
    Background task: Poll stream_events for new chat_message rows and feed to detector.
    Runs every CHAT_POLLER_INTERVAL seconds.
    Tracks last-processed ID per streamer to avoid double-processing.
    On first run, initializes markers to current MAX id per streamer to skip backlog.
    """
    global _chat_poller_last_id

    # Initialize backlog markers on first run (skip pre-existing rows)
    await _initialize_chat_poller_markers()

    while not stop_event.is_set():
        try:
            db = SessionLocal()
            try:
                # Get all streamers with recent chat events
                recent_events = db.query(StreamEvent).filter(
                    StreamEvent.event_type == "chat_message"
                ).order_by(StreamEvent.id.asc()).all()

                if not recent_events:
                    await asyncio.sleep(CHAT_POLLER_INTERVAL)
                    continue

                # Group by streamer_id
                from collections import defaultdict
                events_by_streamer = defaultdict(list)
                for event in recent_events:
                    events_by_streamer[event.streamer_id].append(event)

                # Process new events per streamer
                from backend.core.moment_detector import get_detector
                detector = get_detector()

                for streamer_id, events in events_by_streamer.items():
                    # Get marker for this streamer
                    last_processed_id = _chat_poller_last_id.get(streamer_id)

                    # If streamer not yet initialized (appeared after startup),
                    # initialize to current max_id to skip their backlog
                    if last_processed_id is None:
                        current_max_id = max([e.id for e in events]) if events else 0
                        _chat_poller_last_id[streamer_id] = current_max_id - 1 if current_max_id > 0 else 0
                        last_processed_id = _chat_poller_last_id[streamer_id]
                        logger.info(f"[CHAT→POLLER] Initialized new streamer {streamer_id}: setting marker to {last_processed_id}")

                    # Find events newer than marker
                    new_events = [e for e in events if e.id > last_processed_id]

                    if not new_events:
                        logger.debug(f"[CHAT→POLLER] Streamer {streamer_id}: last_id={last_processed_id}, no new rows")
                        continue

                    # Feed to detector and advance marker
                    messages_fed = 0
                    for event in new_events:
                        # Feed to detector
                        detector.add_chat_message(
                            streamer_id=event.streamer_id,
                            source=event.platform,  # "youtube" | "twitch"
                            message=event.message or ""
                        )
                        messages_fed += 1
                        _chat_poller_last_id[streamer_id] = event.id

                    # Debug log with marker position and new rows found
                    logger.info(f"[CHAT→POLLER] Streamer {streamer_id}: last_id={last_processed_id}, found {messages_fed} new rows (marker now={_chat_poller_last_id[streamer_id]})")
                    logger.info(f"[CHAT→DETECTOR] Streamer {streamer_id}: fed {messages_fed} messages")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"[CHAT→DETECTOR] Poller error: {e}")

        await asyncio.sleep(CHAT_POLLER_INTERVAL)


async def ingestion_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            youtube_conns = db.query(PlatformConnection).filter(PlatformConnection.platform == "youtube").all()
            twitch_conns = db.query(PlatformConnection).filter(PlatformConnection.platform == "twitch").all()
        finally:
            db.close()

        for conn in youtube_conns:
            try:
                await poll_youtube_once(conn)
            except Exception:
                pass

        for conn in twitch_conns:
            try:
                await auto_subscribe_twitch(conn)
            except Exception:
                pass

        await asyncio.sleep(YOUTUBE_POLL_INTERVAL)
