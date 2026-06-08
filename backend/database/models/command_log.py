from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from backend.database.session import Base

class CommandLog(Base):
    __tablename__ = "command_logs"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(String)      # What you said
    intent = Column(String)        # e.g., "switch_scene"
    action = Column(String)        # e.g., "gaming_scene"
    status = Column(String)        # e.g., "success"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
