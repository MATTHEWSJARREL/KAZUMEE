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
        self.mock_clips = [
            {
                "id": "demo_clip_1",
                "title": "Epic Speed Run",
                "url": "https://example.com/clip1.mp4",
                "platform": "Twitch",
                "description": "Amazing speed run completion",
                "tags": ["gaming", "speedrun", "epic"]
            },
            {
                "id": "demo_clip_2",
                "title": "Funny Fail Moment",
                "url": "https://example.com/clip2.mp4",
                "platform": "YouTube",
                "description": "Hilarious gaming fail",
                "tags": ["funny", "fail", "gaming"]
            },
            {
                "id": "demo_clip_3",
                "title": "Pro Player Highlight",
                "url": "https://example.com/clip3.mp4",
                "platform": "Twitch",
                "description": "Professional gameplay highlight",
                "tags": ["pro", "highlight", "skill"]
            }
        ]
        logger.info("VectorClipService initialized with demo data")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration with defaults."""
        defaults = {
            "groq_api_key": "",
            "obs_password": "",
            "obs_host": "localhost",
            "obs_port": 4455,
            "clips_folder": "backend/data/clips",
            "vector_db_path": "backend/data/vector_db",
            "log_level": "INFO",
            "retry_attempts": 3,
            "retry_delay": 2.0,
            "embedding_model": "all-MiniLM-L6-v2",
            "max_search_results": 5,
            "auto_index_clips": True,
            "websocket_port": 8765
        }

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                defaults.update(user_config)
                logger.info("Configuration loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load config: {e}. Using defaults.")
        else:
            logger.warning(f"Config file {config_path} not found. Using defaults.")

        return defaults

    def _generate_clip_id(self, file_path: str) -> str:
        """Generate a unique ID for a clip based on its path."""
        return hashlib.md5(file_path.encode()).hexdigest()

    def _extract_metadata_from_filename(self, filename: str) -> Dict:
        """Extract basic metadata from filename (can be enhanced with actual clip analysis)."""
        # Simple extraction - in production, use ffmpeg or similar to get real metadata
        name = os.path.splitext(filename)[0]
        tags = []

        # Extract potential tags from filename
        if "funny" in name.lower():
            tags.append("#Funny")
        if "skill" in name.lower() or "pro" in name.lower():
            tags.append("#HighSkill")
        if "fail" in name.lower():
            tags.append("#Fail")
        if "win" in name.lower():
            tags.append("#Win")

        return {
            "title": name,
            "tags": tags,
            "timestamp": datetime.now().isoformat(),
            "summary_text": f"Clip: {name}"  # Placeholder - would be AI-generated summary
        }

    def index_clip(self, file_path: str) -> bool:
        """Index a single clip in the vector database."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Clip file not found: {file_path}")
                return False

            clip_id = self._generate_clip_id(file_path)
            metadata = self._extract_metadata_from_filename(os.path.basename(file_path))

            # Create embedding from the summary text
            embedding = self.embedding_model.encode(metadata["summary_text"]).tolist()

            # Prepare metadata for ChromaDB
            chroma_metadata = {
                "file_path": file_path,
                "title": metadata["title"],
                "timestamp": metadata["timestamp"],
                "tags": json.dumps(metadata["tags"]),
                "summary_text": metadata["summary_text"]
            }

            # Add to collection
            self.collection.add(
                ids=[clip_id],
                embeddings=[embedding],
                metadatas=[chroma_metadata],
                documents=[metadata["summary_text"]]
            )

            logger.info(f"Indexed clip: {metadata['title']}")
            return True

        except Exception as e:
            logger.error(f"Failed to index clip {file_path}: {e}")
            return False

    def index_all_clips(self) -> int:
        """Index all clips in the configured clips folder."""
        clips_folder = self.config.get("clips_folder", "backend/data/clips")
        indexed_count = 0

        if not os.path.exists(clips_folder):
            logger.warning(f"Clips folder not found: {clips_folder}")
            return 0

        for root, _, files in os.walk(clips_folder):
            for file in files:
                if file.lower().endswith(('.mp4', '.mkv', '.mov', '.avi')):
                    file_path = os.path.join(root, file)
                    clip_id = self._generate_clip_id(file_path)

                    # Check if already indexed
                    try:
                        existing = self.collection.get(ids=[clip_id])
                        if existing['ids']:
                            continue  # Already indexed
                    except:
                        pass  # Not indexed yet

                    if self.index_clip(file_path):
                        indexed_count += 1

        logger.info(f"Indexed {indexed_count} new clips")
        return indexed_count

    def search_clips(self, query: str, limit: Optional[int] = None) -> List[Dict]:
        """Search clips using semantic similarity."""
        try:
            if limit is None:
                limit = self.max_results

            # Generate embedding for the query
            query_embedding = self.embedding_model.encode(query).tolist()

            # Search the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=['metadatas', 'distances', 'documents']
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, clip_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]

                    formatted_results.append({
                        "id": clip_id,
                        "title": metadata.get("title", "Unknown"),
                        "file_path": metadata.get("file_path", ""),
                        "summary_text": metadata.get("summary_text", ""),
                        "tags": json.loads(metadata.get("tags", "[]")),
                        "timestamp": metadata.get("timestamp", ""),
                        "score": 1.0 - distance,  # Convert distance to similarity score
                        "source": "vector_db"
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_clip_by_id(self, clip_id: str) -> Optional[Dict]:
        """Retrieve a specific clip by ID."""
        try:
            result = self.collection.get(ids=[clip_id], include=['metadatas'])
            if result['ids'] and result['metadatas']:
                metadata = result['metadatas'][0]
                return {
                    "id": clip_id,
                    "title": metadata.get("title", "Unknown"),
                    "file_path": metadata.get("file_path", ""),
                    "summary_text": metadata.get("summary_text", ""),
                    "tags": json.loads(metadata.get("tags", "[]")),
                    "timestamp": metadata.get("timestamp", ""),
                    "source": "vector_db"
                }
        except Exception as e:
            logger.error(f"Failed to get clip {clip_id}: {e}")
        return None

    def delete_clip(self, clip_id: str) -> bool:
        """Remove a clip from the vector database."""
        try:
            self.collection.delete(ids=[clip_id])
            logger.info(f"Deleted clip {clip_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete clip {clip_id}: {e}")
            return False

    async def auto_index_worker(self):
        """Background worker to automatically index new clips."""
        while True:
            try:
                if self.config.get("auto_index_clips", True):
                    self.index_all_clips()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Auto-index worker error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
