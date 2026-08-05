from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from backend.database.session import Base


class AgentToken(Base):
    __tablename__ = "agent_tokens"

    id = Column(Integer, primary_key=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)  # SHA256 hash of token

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)  # NULL = active
