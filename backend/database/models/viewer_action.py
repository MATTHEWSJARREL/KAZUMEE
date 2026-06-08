from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from backend.database.session import Base


class ViewerAction(Base):
    __tablename__ = "viewer_actions"

    id = Column(Integer, primary_key=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False, index=True)
    viewer_id = Column(Integer, ForeignKey("viewers.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False)  # vote_scene | export_clip | trigger_sound
    target = Column(String, nullable=True)  # scene name, clip id, sound id
    payload = Column(JSON, nullable=True)
    cost = Column(Integer, default=0)
    status = Column(String, default="queued")  # queued | executed | denied | error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
