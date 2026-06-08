from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from backend.database.session import Base

class Viewer(Base):
    __tablename__ = "viewers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    active_streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=True, index=True)
    username = Column(String, nullable=False)
    platform_user_id = Column(String, unique=True)
    is_subscriber = Column(Boolean, default=False)
    tier = Column(String, default="free")  # free, premium, vip
    
    # Economy & Engagement
    credits = Column(Integer, default=100) 
    total_spent = Column(Integer, default=0)
    preferences_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
