from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import os
import httpx

from backend.core.auth import get_current_user
from backend.core.search import search_links

router = APIRouter(prefix="/api/moment-finder", tags=["MomentFinder"])


class MomentFinderRequest(BaseModel):
    query: str
    platforms: list[str] | None = None
    limit: int | None = 5


def _build_site_query(platforms: list[str]) -> str:
    sites = {
        "twitch": "twitch.tv",
        "youtube": "youtube.com",
        "tiktok": "tiktok.com",
        "kick": "kick.com",
    }
    filters = [f"site:{sites[p]}" for p in platforms if p in sites]
    if not filters:
        return ""
    return " (" + " OR ".join(filters) + ")"


async def _search_serper(query: str, limit: int) -> list[dict]:
    return await search_links(query, limit)


async def _search_serpapi(query: str, limit: int) -> list[dict]:
    api_key = os.getenv("SERPAPI_KEY", "")
    if not api_key:
        return []
    params = {"engine": "google", "q": query, "api_key": api_key, "num": limit}
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get("https://serpapi.com/search.json", params=params)
    if res.status_code >= 300:
        return []
    data = res.json()
    items = data.get("organic_results", [])[:limit]
    return [
        {
            "title": item.get("title"),
            "url": item.get("link"),
            "snippet": item.get("snippet"),
        }
        for item in items
    ]


@router.post("/search")
async def moment_finder_search(request: Request, payload: MomentFinderRequest):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")

    query = (payload.query or "").strip()
    if not query:
        return {"status": "error", "message": "query required", "results": []}

    platforms = payload.platforms or ["twitch", "youtube", "tiktok", "kick"]
    limit = max(1, min(payload.limit or 5, 10))
    full_query = query + _build_site_query(platforms)

    provider = os.getenv("SEARCH_PROVIDER", "serper").lower()
    if provider == "serpapi":
        results = await _search_serpapi(full_query, limit)
    else:
        results = await _search_serper(full_query, limit)

    if not results:
        return {
            "status": "no_results",
            "provider": provider,
            "results": [],
            "message": "No results or search provider not configured.",
        }

    return {"status": "success", "provider": provider, "results": results}


class LinkSearchRequest(BaseModel):
    query: str
    limit: int | None = 2


@router.post("/links")
async def link_search(request: Request, payload: LinkSearchRequest):
    query = (payload.query or "").strip()
    if not query:
        return {"status": "error", "message": "query required", "results": []}
    limit = max(1, min(payload.limit or 2, 5))
    results = await search_links(query, limit)
    if not results:
        return {"status": "no_results", "results": [], "message": "No results or search provider not configured."}
    return {"status": "success", "results": results}
