from sqlalchemy import Column, Integer, LargeBinary, Float, Boolean, ForeignKey, DateTime, String
from sqlalchemy.sql import func
from backend.database.session import Base

class StreamerVoiceEmbedding(Base):
    """Stores the voice embedding vector for a streamer's voice fingerprint."""
    __tablename__ = "streamer_voice_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False, unique=True, index=True)
    # The 150-dimensional embedding vector as float32 bytes (~600 bytes)
    embedding = Column(LargeBinary, nullable=False)
    # Cosine similarity threshold (0.0–1.0); default 0.75 per spec
    similarity_threshold = Column(Float, default=0.75)
    # Raw sample used for verification
    sample_text = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)