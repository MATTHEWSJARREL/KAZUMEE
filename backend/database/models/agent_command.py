from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from backend.database.session import Base


class AgentCommand(Base):
    __tablename__ = "agent_commands"

    id = Column(Integer, primary_key=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False, index=True)
    command_id = Column(Integer, ForeignKey("commands.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(String, default="pending")  # pending, sent, executed, error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
