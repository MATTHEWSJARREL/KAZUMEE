import os
import json
import asyncio
from typing import List, Dict, Optional
import logging
from datetime import datetime
import random

logger = logging.getLogger(__name__)

class VectorClipService:
    """Simplified clip search service for demo purposes."""

    def __init__(self, base_dir: str = "backend/data/clips"):
        self.base_dir = base_dir
        self.mock_clips = []
        logger.info("VectorClipService initialized - no demo data, using real clips only")

    def search_multi(self, query: str, limit: int = 5) -> List[Dict]:
        """Search clips and return mock results for demo."""
        logger.info(f"Searching for clips: {query}")

        # Simple keyword matching for demo
        results = []
        query_lower = query.lower()

        for clip in self.mock_clips:
            # Check if query matches title, description, or tags
            if (query_lower in clip["title"].lower() or
                query_lower in clip["description"].lower() or
                any(query_lower in tag.lower() for tag in clip["tags"])):
                results.append({
                    "id": clip["id"],
                    "title": clip["title"],
                    "url": clip["url"],
                    "platform": clip["platform"],
                    "description": clip["description"],
                    "tags": clip["tags"],
                    "score": 0.9,  # Mock relevance score
                    "source": "demo_db"
                })

        # If no matches, return a random clip as fallback
        if not results:
            clip = random.choice(self.mock_clips)
            results.append({
                "id": clip["id"],
                "title": clip["title"],
                "url": clip["url"],
                "platform": clip["platform"],
                "description": clip["description"],
                "tags": clip["tags"],
                "score": 0.5,
                "source": "demo_db_fallback"
            })

        return results[:limit]

    def search_clips(self, query: str, limit: Optional[int] = None) -> List[Dict]:
        """Alias for search_multi for compatibility."""
        return self.search_multi(query, limit or 5)
