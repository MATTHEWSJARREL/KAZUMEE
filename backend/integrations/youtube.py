import os
import httpx
from typing import Optional
from google.oauth2.service_account import Credentials
from google_auth_httplib2 import AuthorizedHttp
import googleapiclient.discovery

YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

class YouTubeClient:
    def __init__(self):
        self.api_key = YOUTUBE_API_KEY
        self.service = None
        self._init_service()

    def _init_service(self):
        """Initialize YouTube API service"""
        if self.api_key:
            self.service = googleapiclient.discovery.build(
                "youtube", "v3", developerKey=self.api_key
            )

    async def get_channel_by_username(self, username: str) -> Optional[dict]:
        """Get channel info by username"""
        try:
            if not self.service:
                return None

            request = self.service.search().list(
                part="snippet",
                forUsername=username,
                type="channel",
                maxResults=1
            )
            response = request.execute()

            if response.get("items"):
                channel_id = response["items"][0]["snippet"]["channelId"]
                return {"channel_id": channel_id, "username": username}
            return None
        except Exception as e:
            print(f"Error getting YouTube channel: {e}")
            return None

    async def is_channel_live(self, channel_id: str) -> bool:
        """Check if a channel is currently live streaming"""
        try:
            if not self.service:
                return False

            # Get channel's live streams
            request = self.service.search().list(
                part="snippet",
                channelId=channel_id,
                type="video",
                eventType="live",
                maxResults=1
            )
            response = request.execute()

            # If there are items, channel is live
            return len(response.get("items", [])) > 0
        except Exception as e:
            print(f"Error checking YouTube live status: {e}")
            return False

    async def get_live_stream_info(self, channel_id: str) -> Optional[dict]:
        """Get info about current live stream"""
        try:
            if not self.service:
                return None

            request = self.service.search().list(
                part="snippet",
                channelId=channel_id,
                type="video",
                eventType="live",
                maxResults=1
            )
            response = request.execute()

            if response.get("items"):
                item = response["items"][0]
                return {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "channel_id": channel_id,
                    "is_live": True
                }
            return None
        except Exception as e:
            print(f"Error getting YouTube live stream info: {e}")
            return None

# Global instance
_youtube_client: Optional[YouTubeClient] = None

def get_youtube_client() -> YouTubeClient:
    global _youtube_client
    if _youtube_client is None:
        _youtube_client = YouTubeClient()
    return _youtube_client
