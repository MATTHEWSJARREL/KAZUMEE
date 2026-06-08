from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from backend.database.session import Base

class Community(Base):
    __tablename__ = "communities"

    id = Column(Integer, primary_key=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False)
    name = Column(String, nullable=False)
    language = Column(String)
    culture_profile = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
