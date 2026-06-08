from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from backend.database.session import Base


class MLModelArtifact(Base):
    __tablename__ = "ml_model_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False, index=True)
    model_name = Column(String(64), nullable=False, default="taste_profile_v1", index=True)
    model_version = Column(Integer, nullable=False)
    model_state = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)
    train_samples = Column(Integer, nullable=False, default=0)
    holdout_samples = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
