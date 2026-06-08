from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from backend.database.session import Base


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=True, index=True)
    role = Column(String(16), nullable=False)  # user | assistant
    mode = Column(String(16), nullable=False, default="ask")  # ask | command
    content = Column(Text, nullable=False)
    command_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
