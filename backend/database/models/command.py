from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from backend.database.session import Base

class Command(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    stream_session_id = Column(Integer, ForeignKey("stream_sessions.id"), nullable=False)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=True, index=True)
    
    issued_by_type = Column(String) # viewer, streamer, ai_observer
    issued_by_id = Column(Integer)
    
    command_text = Column(String)
    intent = Column(String)
    
    #Explainability & Bounties
    ai_reasoning = Column(String)
    confidence_score = Column(Float, default=1.0)
    credit_cost = Column(Integer, default=0)
    
    execution_target = Column(String)
    status = Column(String, default="pending") # pending, approved, rejected, executed
    priority_level = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
