"""
Advanced Recap Engine with Groq AI + YouTube/Twitch Clip Matching
Generates AI-powered recaps with linked clips for viewers
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import os
from datetime import datetime, timedelta, timezone
from collections import Counter
import re
import httpx
import json
from sqlalchemy.orm import Session

from backend.core.logger import get_logger
from backend.database.session import get_db
from backend.database.models.stream_event import StreamEvent

logger = get_logger(__name__)
router = APIRouter(prefix="/api/viewer", tags=["recap-engine"])


class RecapTopic(BaseModel):
    topic: str
    confidence: float
    keywords: List[str]


class ClipLink(BaseModel):
    title: str
    url: str
    platform: str  # "youtube", "twitch", "social"
    source: str  # "auto-created", "user-created", "platform-clips"


class AdvancedRecap(BaseModel):
    summary: str
    mood: str
    topics: List[RecapTopic]
    clips: List[ClipLink]
    duration: str
    key_moments: List[str]


async def extract_topics_with_groq(messages: List[str]) -> List[RecapTopic]:
    """Use Groq to intelligently extract topics from chat"""
    try:
        if not messages:
            return []

        # Join recent messages (limit to avoid token overflow)
        chat_text = "\n".join(messages[-200:])  # Last 200 messages

        prompt = f"""Analyze this stream chat and extract the TOP 3 topics/moments that viewers are talking about.

CHAT:
{chat_text}

Return ONLY a JSON array with this format (no markdown, no extras):
[
  {{"topic": "topic name", "confidence": 0.95, "keywords": ["word1", "word2"]}},
  {{"topic": "another topic", "confidence": 0.87, "keywords": ["word1", "word2"]}}
]

Focus on:
- Game/content moments (clutches, fails, funny)
- Drama or controversy
- Achievement milestones
- Chat reactions (hype, sadness, etc)

Be concise. Only JSON."""

        # Use backend Groq proxy
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/groq/chat",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "system_prompt": "You are an expert at analyzing live stream chat. Extract key topics as JSON only.",
                    "temperature": 0.3,
                    "max_tokens": 300,
                },
                timeout=30.0,
            )

        if response.status_code != 200:
            logger.warning(f"Groq API error: {response.status_code}")
            return []

        data = response.json()
        response_text = data.get("response", "").strip()

        try:
            topics_data = json.loads(response_text)
            return [
                RecapTopic(
                    topic=t.get("topic", ""),
                    confidence=float(t.get("confidence", 0.5)),
                    keywords=t.get("keywords", []),
                )
                for t in topics_data
                if t.get("topic")
            ]
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Groq response: {response_text}, {e}")
            return []

    except Exception as e:
        logger.error(f"Groq topic extraction error: {e}")
        return []


async def search_youtube_clips(
    channel_name: str, topics: List[RecapTopic]
) -> List[ClipLink]:
    """Search YouTube for clips matching the topics"""
    try:
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            logger.info("YouTube API key not configured")
            return []

        # Search for clips based on topics
        clips = []
        async with httpx.AsyncClient() as client:
            for topic in topics[:2]:  # Top 2 topics
                query = f"{channel_name} {topic.topic}"

                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "key": api_key,
                        "q": query,
                        "type": "video",
                        "part": "snippet",
                        "maxResults": 3,
                        "order": "date",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", []):
                        video_id = item["id"].get("videoId")
                        if video_id:
                            clips.append(
                                ClipLink(
                                    title=item["snippet"]["title"],
                                    url=f"https://youtube.com/watch?v={video_id}",
                                    platform="youtube",
                                    source="platform-clips",
                                )
                            )

        return clips[:3]  # Return top 3

    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return []


async def search_twitch_clips(
    channel_name: str, topics: List[RecapTopic]
) -> List[ClipLink]:
    """Search Twitch for clips matching the topics"""
    try:
        client_id = os.getenv("TWITCH_CLIENT_ID")
        access_token = os.getenv("TWITCH_ACCESS_TOKEN")

        if not client_id or not access_token:
            logger.info("Twitch API credentials not configured")
            return []

        clips = []
        async with httpx.AsyncClient() as client:
            headers = {
                "Client-ID": client_id,
                "Authorization": f"Bearer {access_token}",
            }

            for topic in topics[:2]:  # Top 2 topics
                response = await client.get(
                    "https://api.twitch.tv/helix/clips",
                    params={
                        "broadcaster_login": channel_name.lower(),
                        "first": 3,
                    },
                    headers=headers,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    for clip in data.get("data", []):
                        clips.append(
                            ClipLink(
                                title=clip["title"],
                                url=clip["url"],
                                platform="twitch",
                                source="platform-clips",
                            )
                        )

        return clips[:3]  # Return top 3

    except Exception as e:
        logger.error(f"Twitch search error: {e}")
        return []


async def search_social_media_clips(
    channel_name: str, topics: List[RecapTopic]
) -> List[ClipLink]:
    """Search social media (Twitter, TikTok) for clip links"""
    try:
        # Social media APIs are optional for v1
        # Can be added later if needed
        return []
    except Exception as e:
        logger.error(f"Social media search error: {e}")
        return []


def infer_mood_from_chat(messages: List[str]) -> str:
    """Infer stream mood from chat sentiment"""
    chat_text = " ".join(messages).lower()

    hype_words = [
        "poggers",
        "pog",
        "lets go",
        "insane",
        "clutch",
        "omg",
        "wow",
        "fire",
        "gg",
        "sick",
    ]
    sad_words = ["rip", "sadge", "oof", "unlucky", "dead", "fail", "cringe"]
    funny_words = ["lmao", "lol", "xd", "funny", "hilarious", "comedy"]

    hype_count = sum(chat_text.count(word) for word in hype_words)
    sad_count = sum(chat_text.count(word) for word in sad_words)
    funny_count = sum(chat_text.count(word) for word in funny_words)

    if hype_count > sad_count and hype_count > funny_count:
        return "🔥 Hype"
    elif sad_count > hype_count:
        return "😅 Tough moments"
    elif funny_count > 0:
        return "😂 Funny moments"
    else:
        return "👀 Engaging"


@router.get("/recap/advanced")
async def get_advanced_recap(
    request: Request,
    db: Session = Depends(get_db),
    streamer_id: int = None,
    mode: str = "quick",
):
    """
    Get AI-powered recap with linked clips
    Viewer can watch stream on YouTube/Twitch while reading recap with clip links
    """
    try:
        if not streamer_id:
            raise HTTPException(status_code=400, detail="streamer_id required")

        # Get recent chat messages (last 3 hours)
        window_since = datetime.now(timezone.utc) - timedelta(hours=3)
        rows = (
            db.query(StreamEvent)
            .filter(
                StreamEvent.streamer_id == streamer_id,
                StreamEvent.created_at >= window_since,
                StreamEvent.message.isnot(None),
            )
            .order_by(StreamEvent.created_at.desc())
            .limit(500)
            .all()
        )

        if not rows:
            return {
                "recap": "No chat data yet. Check back when the stream is more active!",
                "topics": [],
                "clips": [],
                "mood": "👀 Starting",
            }

        messages = [r.message for r in rows if r.message]

        # 1. Extract topics with Groq
        topics = await extract_topics_with_groq(messages)

        # 2. Search for clips (YouTube > Twitch > Social)
        clips: List[ClipLink] = []

        # Try YouTube first
        yt_clips = await search_youtube_clips("streamer_name", topics)
        clips.extend(yt_clips)

        # Fall back to Twitch
        if not clips:
            twitch_clips = await search_twitch_clips("streamer_name", topics)
            clips.extend(twitch_clips)

        # Fall back to social media
        if not clips:
            social_clips = await search_social_media_clips("streamer_name", topics)
            clips.extend(social_clips)

        # 3. Generate summary
        mood = infer_mood_from_chat(messages)

        topic_text = ", ".join([t.topic for t in topics[:3]])
        summary = f"You missed: {topic_text}. Mood was {mood}."

        # 4. Build response
        return {
            "summary": summary,
            "mood": mood,
            "topics": [
                {"topic": t.topic, "confidence": t.confidence, "keywords": t.keywords}
                for t in topics
            ],
            "clips": [
                {"title": c.title, "url": c.url, "platform": c.platform, "source": c.source}
                for c in clips
            ],
            "duration": f"{len(rows)} messages analyzed",
            "key_moments": [t.topic for t in topics],
        }

    except Exception as e:
        logger.error(f"Advanced recap error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recap/fomo")
async def get_fomo_recap(
    request: Request,
    db: Session = Depends(get_db),
    streamer_id: int = None,
    days_back: int = 7,
):
    """
    Get old clips from past streams (FOMO/lore)
    Shows clip links to past highlights
    """
    try:
        if not streamer_id:
            raise HTTPException(status_code=400, detail="streamer_id required")

        # Get clips from past N days
        window_since = datetime.now(timezone.utc) - timedelta(days=days_back)
        # This would query clip database in production

        return {
            "message": f"Past {days_back} days of highlights would appear here",
            "clips": [],
        }

    except Exception as e:
        logger.error(f"FOMO recap error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
