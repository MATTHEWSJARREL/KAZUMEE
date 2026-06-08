import os
import httpx


async def search_links(query: str, limit: int = 2) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        return []
    limit = max(1, min(limit, 5))

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": max(limit, 3)}
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post("https://google.serper.dev/search", headers=headers, json=payload)
    if res.status_code >= 300:
        return []
    data = res.json()
    items = data.get("organic", [])[:limit]
    return [
        {
            "title": item.get("title") or "Link",
            "url": item.get("link"),
            "snippet": item.get("snippet"),
        }
        for item in items
        if item.get("link")
    ]


def format_links_for_chat(links: list[dict]) -> str:
    if not links:
        return ""
    lines = []
    for idx, item in enumerate(links, start=1):
        title = item.get("title") or "Link"
        url = item.get("url") or ""
        lines.append(f"{idx}. {title} - {url}")
    return "Links:\n" + "\n".join(lines)
