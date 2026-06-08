from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from backend.database.session import Base

class Streamer(Base):
    __tablename__ = "streamers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    platform = Column(String)
    
    # Production Settings
    operation_mode = Column(String, default="hybrid")  # manual, auto, hybrid
    auto_approve_min_tier = Column(String, default="vip")
    policy_json = Column(JSON, nullable=True)
    taste_profile = Column(JSON, nullable=True)
    settings_json = Column(JSON, nullable=True)
    subscription_tier = Column(String, default="free")
    subscription_status = Column(String, default="inactive")
    subscription_will_cancel = Column(Boolean, default=False)
    
    timezone = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
