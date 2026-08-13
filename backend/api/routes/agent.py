"""
WebSocket endpoint for autonomous clipping agents.
Agents (running on streamer PCs) connect here and wait for clip commands.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Optional
import json
import logging
from datetime import datetime

from backend.core.auth import (
    get_streamer_id_for_user,
    get_current_user,
    create_agent_token,
    verify_agent_token,
    get_agent_token_metadata,
)
from backend.api.agent_protocol import AGENT_WS_PATH, CLIP_COMMAND, AGENT_ONLINE, PING_MESSAGE, PONG_MESSAGE

logger = logging.getLogger(__name__)

router = APIRouter()

# Track connected agents by streamer_id: { streamer_id -> (ws, last_seen) }
connected_agents: Dict[int, dict] = {}


@router.websocket(AGENT_WS_PATH)
async def websocket_agent_endpoint(websocket: WebSocket):
    """
    Agent WebSocket connection.

    Agent connects with either:
    - Authorization header: Authorization: Bearer <AGENT_TOKEN>
    - Query param (fallback for testing): ?token=<AGENT_TOKEN>

    Cloud sends: {"cmd": "clip"} → Agent saves replay buffer
    Agent sends: {"type": "agent_online"} → Registration

    CRITICAL: Token is verified before accept(); never logged (security).
    """

    # Extract token from Authorization header first (preferred)
    token = None
    auth_header = websocket.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    # Fallback to query param for testing (not recommended for production)
    if not token:
        token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008, reason="No token provided")
        return

    # Verify agent token and get streamer_id
    # (token is NOT logged anywhere — verified locally, result only)
    streamer_id = verify_agent_token(token)
    if not streamer_id:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    await websocket.accept()

    # Register this agent with timestamp
    connected_agents[streamer_id] = {
        "ws": websocket,
        "last_seen": datetime.utcnow()
    }
    logger.info(f"[AGENT REGISTRY] ✅ Agent online for streamer {streamer_id} | "
                f"Total connected: {len(connected_agents)} | Registry: {list(connected_agents.keys())}")

    try:
        import asyncio

        async def keepalive_pings():
            """Send ping every 25s to keep WebSocket alive (prevent Railway timeout ~60s)."""
            ping_count = 0
            while streamer_id in connected_agents:
                await asyncio.sleep(25)
                try:
                    if streamer_id in connected_agents:
                        ws = connected_agents[streamer_id]["ws"]
                        await ws.send_json({"type": "ping"})
                        ping_count += 1
                        logger.debug(f"[KEEPALIVE] Ping sent to streamer {streamer_id} (#{ping_count})")
                except Exception as e:
                    logger.warning(f"[KEEPALIVE] Failed to send ping to streamer {streamer_id}: {e}")

        # Start keepalive task
        keepalive_task = asyncio.create_task(keepalive_pings())

        try:
            while True:
                # Wait for messages from agent (heartbeats, etc)
                message = await websocket.receive_text()
                connected_agents[streamer_id]["last_seen"] = datetime.utcnow()

                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "agent_online":
                        logger.info(f"Streamer {streamer_id}: agent online")
                    elif msg_type == "pong":
                        pass  # Heartbeat response, ignore
                    elif msg_type == "clip_uploaded":
                        logger.info(f"Streamer {streamer_id}: clip uploaded successfully")
                    else:
                        logger.debug(f"Streamer {streamer_id}: unknown message type {msg_type}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from agent: {message}")
        finally:
            keepalive_task.cancel()

    except WebSocketDisconnect:
        logger.info(f"Agent disconnected: streamer {streamer_id}")
        if streamer_id in connected_agents:
            del connected_agents[streamer_id]
    except Exception as e:
        logger.error(f"WebSocket error for streamer {streamer_id}: {e}")
        if streamer_id in connected_agents:
            del connected_agents[streamer_id]


async def send_clip_command_to_agent(streamer_id: int) -> bool:
    """
    Send clip command to connected agent for this streamer.
    Returns True if agent was online and command sent.
    """
    # Log the attempt with full debug info
    all_connected_ids = list(connected_agents.keys())
    logger.info(f"[CLIP COMMAND] Moment detected for streamer {streamer_id} | "
                f"Connected agents: {all_connected_ids}")

    if streamer_id not in connected_agents:
        logger.warning(f"[CLIP COMMAND] ❌ No agent connected for streamer {streamer_id} | "
                      f"Available: {all_connected_ids}")
        return False

    try:
        agent_info = connected_agents[streamer_id]
        ws = agent_info["ws"]
        await ws.send_json(CLIP_COMMAND)
        logger.info(f"[CLIP COMMAND] ✅ Sent clip command to streamer {streamer_id}")
        return True
    except Exception as e:
        logger.error(f"[CLIP COMMAND] ❌ Failed to send clip command to streamer {streamer_id}: {e}")
        # Remove the dead connection
        if streamer_id in connected_agents:
            del connected_agents[streamer_id]
        return False


# ==============================================================================
# TOKEN VERIFICATION
# ==============================================================================

@router.post("/agent/token-verify")
async def verify_token(request: Request):
    """
    Quick token validation endpoint (used by agent on first-run).
    No auth required — the token itself proves identity.
    """
    auth_header = request.headers.get("Authorization", "")
    token = None

    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    streamer_id = verify_agent_token(token)
    if not streamer_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {"valid": True, "streamer_id": streamer_id}


# ==============================================================================
# TOKEN ENDPOINTS
# ==============================================================================

@router.get("/agent/token")
async def get_agent_token_info(request: Request, current_user = Depends(get_current_user)):
    """Get metadata about this streamer's active agent token (never return the token itself)."""
    if not current_user or current_user.role != "streamer":
        raise HTTPException(status_code=403, detail="Only streamers can view agent tokens")

    streamer_id = get_streamer_id_for_user(current_user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="No streamer found for this user")

    metadata = get_agent_token_metadata(streamer_id)
    if not metadata:
        return {
            "exists": False,
            "message": "No active agent token. Generate one with POST /api/agent/token"
        }

    return metadata


@router.post("/agent/token")
async def create_new_agent_token(request: Request, current_user = Depends(get_current_user)):
    """
    Generate a new long-lived agent token for this streamer.

    Returns the RAW token (shown once). Store it immediately—it won't be retrievable again.
    Regenerating revokes the previous token.
    """
    if not current_user or current_user.role != "streamer":
        raise HTTPException(status_code=403, detail="Only streamers can generate agent tokens")

    streamer_id = get_streamer_id_for_user(current_user)
    if not streamer_id:
        raise HTTPException(status_code=400, detail="No streamer found for this user")

    try:
        raw_token = create_agent_token(streamer_id, ttl_days=30)
        metadata = get_agent_token_metadata(streamer_id)

        return {
            "token": raw_token,
            "expires_at": metadata["expires_at"],
            "message": "Agent token generated. Store it safely—it won't be shown again. Use it with: curl -H 'Authorization: Bearer YOUR_TOKEN' ... or wss://.../ws/agent?token=YOUR_TOKEN"
        }
    except Exception as e:
        logger.error(f"Failed to create agent token for streamer {streamer_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate token")


# ==============================================================================
# STATUS ENDPOINT
# ==============================================================================

@router.get("/agent/status/{streamer_id}")
async def get_agent_status(streamer_id: int, request: Request, current_user = Depends(get_current_user)):
    """Check if agent is online for a streamer, with last_seen timestamp."""
    if not current_user or current_user.role != "streamer":
        raise HTTPException(status_code=403, detail="Only streamers can check agent status")

    # Verify ownership
    user_streamer_id = get_streamer_id_for_user(current_user)
    if user_streamer_id != streamer_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if streamer_id in connected_agents:
        agent_info = connected_agents[streamer_id]
        return {
            "streamer_id": streamer_id,
            "online": True,
            "status": "ready",
            "last_seen": agent_info["last_seen"].isoformat()
        }
    else:
        return {
            "streamer_id": streamer_id,
            "online": False,
            "status": "offline",
            "last_seen": None
        }
