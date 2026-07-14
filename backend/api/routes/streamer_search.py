from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_

from backend.database.session import SessionLocal
from backend.database.models.streamer import Streamer


router = APIRouter()


# -----------------------------
# Twitch app token (cached 24h)
# -----------------------------
_TWITCH_TOKEN_TTL_SECONDS = 24 * 60 * 60
_twitch_token_cache: Dict[str, Any] = {
    "token": None,
    "expires_at": 0.0,
}
_twitch_token_lock = asyncio.Lock()


# Placeholder values (client id i will add them later)
TWITCH_CLIENT_ID = "client id"
TWITCH_CLIENT_SECRET = "client id"


async def get_twitch_app_token() -> str:
    async with _twitch_token_lock:
        now = time.time()
        token = _twitch_token_cache.get("token")
        expires_at = float(_twitch_token_cache.get("expires_at") or 0)
        if token and now < expires_at:
            return token

        async with httpx.AsyncClient(timeout=15) as client:
            # Twitch client credentials token endpoint
            resp = await client.post(
                "https://id.twitch.tv/oauth2/token",
                params={"grant_type": "client_credentials"},
                auth=(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail={"message": "Twitch token fetch failed", "status": resp.status_code, "body": resp.text},
                )

            data = resp.json()
            token = data.get("access_token")
            if not token:
                raise HTTPException(status_code=502, detail={"message": "Twitch token missing"})

            _twitch_token_cache["token"] = token
            _twitch_token_cache["expires_at"] = now + _TWITCH_TOKEN_TTL_SECONDS
            return token


# -----------------------------
# Unified result helpers
# -----------------------------

def _result(
    *,
    rid: str | int,
    display_name: str,
    platform: str,
    is_live: bool = False,
    viewer_count: int = 0,
    thumbnail_url: Optional[str] = None,
    profile_image_url: Optional[str] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": rid,
        "display_name": display_name,
        "platform": platform,
        "is_live": bool(is_live),
        "viewer_count": int(viewer_count or 0),
        "thumbnail_url": thumbnail_url,
        "profile_image_url": profile_image_url,
        "url": url,
    }


# -----------------------------
# Local Kazumee database search
# -----------------------------

async def search_kazumee(q: str, platform: str) -> List[Dict[str, Any]]:
    if platform not in {"all", "kazumee"}:
        return []

    db = SessionLocal()
    try:
        # Find local streamers by display_name or username containing q
        pattern = f"%{q}%"
        rows: List[Streamer] = (
            db.query(Streamer)
            .filter(
                or_(
                    Streamer.display_name.ilike(pattern),
                    Streamer.username.ilike(pattern),
                )
            )
            .order_by(Streamer.id.asc())
            .limit(10)
            .all()
        )

        # Local DB doesn't have live/viewer info in this codebase; default to not-live.
        results = [
            _result(
                rid=s.id,
                display_name=s.display_name or s.username,
                platform="kazumee",
                is_live=False,
                viewer_count=0,
                thumbnail_url=None,
                profile_image_url=None,
                url=None,
            )
            for s in rows
        ]
        return results
    finally:
        db.close()


# -----------------------------
# Twitch search
# -----------------------------

async def search_twitch(q: str, platform: str) -> List[Dict[str, Any]]:
    if platform not in {"all", "twitch"}:
        return []

    token = await get_twitch_app_token()

    headers = {
        "Client-Id": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        url = (
            "https://api.twitch.tv/helix/search/channels"
            f"?query={httpx.QueryParams({'query': q, 'live_only': 'false', 'first': 10})['query']}"
        )
        # The above is a bit awkward with QueryParams; build explicitly for correctness:
        url = (
            "https://api.twitch.tv/helix/search/channels"
            f"?query={httpx.utils.quote(q)}&live_only=false&first=10"
        )
        resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            return []

        data = resp.json() or {}
        items = data.get("data") or []

        results: List[Dict[str, Any]] = []
        for ch in items:
            display_name = ch.get("broadcaster_login") or ch.get("display_name") or "Unknown"
            # Helix channel search doesn't guarantee live status fields; treat as not-live unless present.
            is_live = bool(ch.get("is_live") or ch.get("live") or False)
            viewer_count = int(ch.get("viewer_count") or 0)

            profile_image_url = None
            thumbnail_url = None
            # Some responses include profile_image_url, but keep safe
            if isinstance(ch.get("thumbnail_url"), str):
                thumbnail_url = ch.get("thumbnail_url")
            if isinstance(ch.get("profile_image_url"), str):
                profile_image_url = ch.get("profile_image_url")
            if isinstance(ch.get("logo"), str) and not profile_image_url:
                profile_image_url = ch.get("logo")

            url_out = None
            if ch.get("broadcaster_login"):
                url_out = f"https://www.twitch.tv/{ch.get('broadcaster_login')}"

            results.append(
                _result(
                    rid=ch.get("id") or ch.get("broadcaster_login") or "",
                    display_name=str(display_name),
                    platform="twitch",
                    is_live=is_live,
                    viewer_count=viewer_count,
                    thumbnail_url=thumbnail_url,
                    profile_image_url=profile_image_url,
                    url=url_out,
                )
            )

        # Order: live first among twitch results
        results.sort(key=lambda r: (not r["is_live"], -r.get("viewer_count", 0)))
        return results


# -----------------------------
# YouTube search
# -----------------------------

YOUTUBE_API_KEY = "YOUTUBE_API_KEY"


async def search_youtube(q: str, platform: str) -> List[Dict[str, Any]]:
    if platform not in {"all", "youtube"}:
        return []

    async with httpx.AsyncClient(timeout=20) as client:
        url = (
            "https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&type=channel&q={httpx.utils.quote(q)}&key={YOUTUBE_API_KEY}&maxResults=8"
        )
        resp = await client.get(url)
        if resp.status_code >= 400:
            return []

        data = resp.json() or {}
        items = data.get("items") or []

        results: List[Dict[str, Any]] = []
        for it in items:
            snippet = it.get("snippet") or {}
            channel_id = it.get("id", {}).get("channelId") or snippet.get("channelId") or ""
            title = snippet.get("title") or "Unknown"

            thumb = snippet.get("thumbnails", {}).get("high") or snippet.get("thumbnails", {}).get("default") or {}
            thumbnail_url = thumb.get("url") if isinstance(thumb, dict) else None

            profile_image_url = snippet.get("thumbnails", {}).get("default", {}).get("url") if isinstance(snippet.get("thumbnails", {}).get("default"), dict) else None

            url_out = f"https://www.youtube.com/channel/{channel_id}" if channel_id else None

            results.append(
                _result(
                    rid=channel_id or title,
                    display_name=str(title),
                    platform="youtube",
                    is_live=False,
                    viewer_count=0,
                    thumbnail_url=thumbnail_url,
                    profile_image_url=profile_image_url,
                    url=url_out,
                )
            )

        return results


# -----------------------------
# Endpoint
# -----------------------------

@router.get("/api/streamers/search")
async def search_streamers(
    q: str = Query(..., min_length=1, description="Search term"),
    platform: str = Query("all", description="kazumee|twitch|youtube|all"),
):
    platform = (platform or "all").strip().lower()
    if platform not in {"all", "kazumee", "twitch", "youtube"}:
        raise HTTPException(status_code=400, detail="Invalid platform")

    # Run all three sources concurrently.
    kazumee_task = search_kazumee(q, platform)
    twitch_task = search_twitch(q, platform)
    youtube_task = search_youtube(q, platform)

    kazumee_results, twitch_results, youtube_results = await asyncio.gather(
        kazumee_task,
        twitch_task,
        youtube_task,
        return_exceptions=False,
    )

    # Merge order:
    # 1) Local Kazumee
    # 2) Live Twitch streamers
    # 3) Others (remaining twitch + youtube)
    live_twitch = [r for r in twitch_results if r.get("is_live")]
    other_twitch = [r for r in twitch_results if not r.get("is_live")]

    merged = [*kazumee_results, *live_twitch, *other_twitch, *youtube_results]

    return {
        "status": "success",
        "query": q,
        "platform": platform,
        "results": merged,
    }

