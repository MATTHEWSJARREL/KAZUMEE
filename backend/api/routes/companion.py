"""
Companion Mode - Track external streams (YouTube, Twitch) for viewers
Allows viewers to watch on native platform + use Kazumi features in companion tab
"""
from fastapi import APIRouter, Request
from typing import Optional
import time
import uuid
import os
import asyncio
import httpx

from backend.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/viewer/companion", tags=["companion"])

# In-memory session storage
_companion_sessions = {}

# Mock streamers for fallback
MOCK_STREAMERS = [
    {
        "id": "1",
        "display_name": "Kai Cenat",
        "username": "KaiCenat",
        "platform": "youtube",
        "is_live": True,
        "profile_image_url": "https://via.placeholder.com/150",
    },
    {
        "id": "2",
        "display_name": "Pokimane",
        "username": "pokimane",
        "platform": "twitch",
        "is_live": True,
        "profile_image_url": "https://via.placeholder.com/150",
    },
    {
        "id": "3",
        "display_name": "Valkyrae",
        "username": "valkyrae",
        "platform": "youtube",
        "is_live": False,
        "profile_image_url": "https://via.placeholder.com/150",
    },
]


@router.post("/track")
async def start_companion_tracking(request: Request):
    """Start tracking an external streamer"""
    try:
        body = await request.json()

        platform = (body.get("platform") or "").lower().strip()
        username = (body.get("username") or body.get("display_name") or "").strip()
        display_name = (body.get("display_name") or username or "").strip()

        # Validate
        if not platform or platform not in ["youtube", "twitch"]:
            return {"error": "Invalid platform", "code": 400}

        if not username or not display_name:
            return {"error": "Username and display_name required", "code": 400}

        # Create session
        session_id = str(uuid.uuid4())[:8]

        companion_session = {
            "session_id": session_id,
            "platform": platform,
            "username": username,
            "display_name": display_name,
            "created_at": time.time(),
            "status": "live",
            "clips": [],
            "recap": None,
            "chat_analysis": None,
        }

        _companion_sessions[session_id] = companion_session
        logger.info(f"Companion session created: {session_id}")

        return {
            "success": True,
            "session_id": session_id,
            "platform": platform,
            "username": username,
            "display_name": display_name,
            "companion_url": f"http://localhost:4000/viewer/companion?session={session_id}&platform={platform}&username={username}",
            "status": "live",
        }

    except Exception as e:
        logger.error(f"Companion track error: {e}", exc_info=True)
        return {"error": str(e), "code": 500}


@router.get("/session/{session_id}")
async def get_companion_session(session_id: str):
    """Get companion session data"""
    try:
        session = _companion_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "code": 404}

        return {
            "session_id": session_id,
            "platform": session["platform"],
            "username": session["username"],
            "display_name": session["display_name"],
            "status": session["status"],
            "clips": session.get("clips", []),
            "recap": session.get("recap") or {
                "duration": f"{int((time.time() - session['created_at']) / 60)} min",
                "summary": f"Watching {session['display_name']} on {session['platform'].upper()}",
                "highlights": ["Stream started", "Viewer connected", "Companion active"],
                "stats": {
                    "watch_time_min": int((time.time() - session["created_at"]) / 60),
                    "clips_created": len(session.get("clips", [])),
                },
            },
            "chat_analysis": session.get("chat_analysis") or {
                "mood": "Engaging",
                "emoji": "👀",
                "top_topics": [session["platform"], "streaming", "content"],
                "chat_per_minute": 0,
            },
        }

    except Exception as e:
        logger.error(f"Get session error: {e}")
        return {"error": str(e), "code": 500}


@router.post("/session/{session_id}/clip")
async def create_companion_clip(session_id: str, request: Request):
    """Create a clip in companion"""
    try:
        session = _companion_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "code": 404}

        body = await request.json()
        title = body.get("title", "Quick Clip")

        clip = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "timestamp": "just now",
            "duration": "0:30",
            "created_at": time.time(),
        }

        session["clips"].insert(0, clip)
        logger.info(f"Clip created: {title}")

        return {
            "success": True,
            "clip_id": clip["id"],
            "title": title,
        }

    except Exception as e:
        logger.error(f"Create clip error: {e}")
        return {"error": str(e), "code": 500}


@router.get("/search")
async def search_streamers_companion(q: str = "") -> dict:
    """Search for streamers on YouTube, Twitch, and other platforms"""
    try:
        if not q.strip():
            return {"results": MOCK_STREAMERS[:3]}

        search_term = q.lower().strip()
        results = []

        # Search YouTube (with timeout protection)
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        if youtube_api_key:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:  # 5s timeout for entire client
                    resp = await client.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={
                            "key": youtube_api_key,
                            "q": search_term,
                            "type": "channel",
                            "part": "snippet",
                            "maxResults": 3,
                            "order": "relevance",
                        },
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("items", []):
                            channel_id = item["id"].get("channelId")
                            if channel_id:
                                results.append({
                                    "id": channel_id,
                                    "display_name": item["snippet"]["title"],
                                    "username": item["snippet"]["title"].lower().replace(" ", ""),
                                    "platform": "youtube",
                                    "is_live": False,
                                    "profile_image_url": item["snippet"]["thumbnails"]["default"]["url"],
                                })
            except Exception as e:
                logger.warning(f"YouTube search failed: {e}")

        # Search Twitch (optional - requires API key)
        twitch_client_id = os.getenv("TWITCH_CLIENT_ID")
        twitch_access_token = os.getenv("TWITCH_ACCESS_TOKEN")

        if twitch_client_id and twitch_access_token:
            try:
                async with httpx.AsyncClient() as client:
                    headers = {
                        "Client-ID": twitch_client_id,
                        "Authorization": f"Bearer {twitch_access_token}",
                    }
                    resp = await client.get(
                        "https://api.twitch.tv/helix/search/channels",
                        params={
                            "query": search_term,
                            "first": 3,
                        },
                        headers=headers,
                        timeout=10.0,
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        for channel in data.get("data", []):
                            results.append({
                                "id": channel["id"],
                                "display_name": channel["display_name"],
                                "username": channel["broadcaster_login"],
                                "platform": "twitch",
                                "is_live": channel["is_live"],
                                "profile_image_url": channel["thumbnail_url"],
                            })
            except Exception as e:
                logger.warning(f"Twitch search failed: {e}")

        # Return real results only (no fallback to dummy data)
        return {"results": results}

    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"results": MOCK_STREAMERS}
