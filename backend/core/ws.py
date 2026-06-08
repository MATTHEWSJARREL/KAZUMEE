"""
Backward-compatibility shim.

Canonical websocket manager lives in backend.api.websockets.
Importing manager from backend.core.ws remains supported for legacy modules.
"""

from backend.api.websockets import manager

__all__ = ["manager"]
