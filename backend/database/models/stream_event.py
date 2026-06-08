from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from backend.database.session import Base


class StreamEvent(Base):
    __tablename__ = "stream_events"

    id = Column(Integer, primary_key=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False, index=True)
    platform = Column(String, nullable=False)  # twitch | youtube
    event_type = Column(String, nullable=False)  # chat_message | follow | sub | etc
    event_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    message = Column(String, nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
