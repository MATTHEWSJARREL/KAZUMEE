"""
Activity feed logging system.
Creates StreamEvent records for each command execution.
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def log_command_executed(
    db: Session,
    streamer_id: int,
    command: str,
    status: str = "success",
    result_message: str = "",
    metadata: Optional[dict] = None,
):
    """
    Log a command execution to the StreamEvent table.
    
    Creates an activity feed entry that appears in the viewer's activity log.
    
    Args:
        db: Database session
        streamer_id: ID of the streamer who executed the command
        command: Command name (e.g., "switch_scene", "mute_mic")
        status: "success", "error", "partial"
        result_message: Human-readable result message
        metadata: Optional dict with additional command context (scene name, device info, etc.)
    """
    try:
        from backend.database.models import StreamEvent
        
        event_data = {
            "command": command,
            "status": status,
            "message": result_message,
        }
        
        # Include metadata if provided
        if metadata:
            event_data.update(metadata)
        
        event = StreamEvent(
            streamer_id=streamer_id,
            event_type="command_handled",
            event_data=event_data,
            created_at=datetime.utcnow(),
        )
        
        db.add(event)
        db.commit()
        
        logger.info(
            f"Logged command_handled event: streamer={streamer_id}, command={command}, status={status}"
        )
    
    except Exception as e:
        logger.warning(f"Failed to log command execution: {e}")
        # Don't raise - activity logging shouldn't block command execution
        try:
            db.rollback()
        except:
            pass
