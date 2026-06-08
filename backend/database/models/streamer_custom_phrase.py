"""
StreamerCustomPhrase model - Custom danger phrases for IRL safety mode.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Index
from datetime import datetime

from .base import Base


class StreamerCustomPhrase(Base):
    """
    Custom danger phrases for individual streamers.
    
    Used in IRL transcription mode to detect user-defined safety phrases.
    Each phrase has a sensitivity threshold for matching.
    """

    __tablename__ = "streamer_custom_phrases"

    id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    streamer_id = Column(Integer, ForeignKey("streamers.id", ondelete="CASCADE"), nullable=False, index=True)
    phrase = Column(String(200), nullable=False)
    sensitivity = Column(Float, default=0.8)  # 0.0-1.0: higher = more strict matching
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_streamer_phrases", "streamer_id", "created_at"),
    )

    def __repr__(self):
        return f"<StreamerCustomPhrase(id={self.id}, streamer_id={self.streamer_id}, phrase='{self.phrase[:30]}')>"
