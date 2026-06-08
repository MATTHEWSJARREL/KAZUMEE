from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Float
from sqlalchemy.sql import func
from backend.database.session import Base

class StreamSession(Base):
    __tablename__ = "stream_sessions"

    id = Column(Integer, primary_key=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    avg_viewers = Column(Integer)
    status = Column(String)
    health_score = Column(Float)
