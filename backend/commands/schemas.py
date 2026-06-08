from pydantic import BaseModel
from typing import Dict, Optional, Literal


class CommandRequest(BaseModel):
    text: str
    metadata: Optional[Dict] = {}
    is_canonical: bool = False
    is_brain: bool = False


class CommandResult(BaseModel):
    status: str
    message: str
    data: Optional[Dict] = None
    # Brain metadata (optional, only present for brain decisions)
    intent: Optional[str] = None
    decision: Optional[Literal["execute", "refuse", "defer"]] = None
    reason: Optional[str] = None
    confidence: Optional[float] = None
