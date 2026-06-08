from sqlalchemy import Column, Integer, Boolean, String, ForeignKey
from backend.database.session import Base

class CommandResult(Base):
    __tablename__ = "command_results"

    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(Integer, ForeignKey("commands.id"), nullable=False)
    success = Column(Boolean)
    response_text = Column(String)
    execution_time_ms = Column(Integer)
    error_message = Column(String)
