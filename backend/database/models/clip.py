from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float, JSON
from sqlalchemy.sql import func
from backend.database.session import Base

class Clip(Base):
    __tablename__ = "clips"

    id = Column(Integer, primary_key=True, index=True)
    stream_session_id = Column(Integer, ForeignKey("stream_sessions.id"), nullable=False)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=True, index=True)

    # Clip metadata
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    file_path = Column(String, nullable=False)  # Path to the clip file
    thumbnail_path = Column(String, nullable=True)  # Path to thumbnail

    # Requester info
    requested_by_type = Column(String, nullable=False)  # 'viewer', 'streamer', 'ai'
    requested_by_id = Column(String, nullable=True)  # User ID or username
    requested_by_name = Column(String, nullable=True)  # Display name

    # Status and approval
    status = Column(String, default="pending")  # 'pending', 'approved', 'rejected', 'deleted'
    is_public = Column(Boolean, default=False)  # Whether approved clips are public
    approved_by = Column(String, nullable=True)  # Who approved it
    approved_at = Column(DateTime(timezone=True), nullable=True)
    export_status = Column(String, nullable=True)  # queued, sent, executed, error
    export_preset = Column(String, nullable=True)  # tiktok | shorts | reels
    export_path = Column(String, nullable=True)
    export_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Content analysis
    duration_seconds = Column(Float, nullable=True)
    content_analysis = Column(JSON, nullable=True)  # Store analysis results
    quality_score = Column(Float, nullable=True)  # AI-determined quality score
    sentiment_score = Column(Float, nullable=True)  # Sentiment analysis

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Additional metadata
    tags = Column(JSON, nullable=True)  # List of tags
    notes = Column(Text, nullable=True)  # Internal notes
