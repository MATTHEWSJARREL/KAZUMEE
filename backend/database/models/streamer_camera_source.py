from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from backend.database.session import Base

class StreamerCameraSource(Base):
    """Maps friendly camera names (facecam, overhead) to OBS source details."""
    __tablename__ = "streamer_camera_sources"

    id = Column(Integer, primary_key=True, index=True)
    streamer_id = Column(Integer, ForeignKey("streamers.id"), nullable=False, index=True)
    friendly_name = Column(String(128), nullable=False)
    obs_source_name = Column(String(256), nullable=False)
    obs_device_id = Column(String(256), nullable=True)
    obs_input_kind = Column(String(64), nullable=True)
    meta_json = Column(JSON, nullable=True)