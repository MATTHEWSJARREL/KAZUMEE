"""
WebSocket endpoint for autonomous clipping agents.
Agents (running on streamer PCs) connect here and wait for clip commands.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict
import json
import logging

from backend.core.auth import get_streamer_id_for_user, verify_stream_access_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Track connected agents by streamer_id
connected_agents: Dict[int, WebSocket] = {}


@router.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    """
    Agent WebSocket connection.

    Agent connects with: wss://kazumee.app/ws/agent?token=USER_TOKEN

    Cloud sends: {"cmd": "clip"} → Agent saves replay buffer
    Agent sends: {"type": "agent_online"} → Registration
    """

    # Extract token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="No token provided")
        return

    # Verify token and get streamer_id
    try:
        streamer_id = verify_stream_access_token(token)
        if not streamer_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        await websocket.close(code=1008, reason="Auth failed")
        return

    await websocket.accept()

    # Register this agent
    connected_agents[streamer_id] = websocket
    logger.info(f"Agent online for streamer {streamer_id}")

    try:
        while True:
            # Wait for messages from agent (heartbeats, etc)
            message = await websocket.receive_text()
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
    if streamer_id not in connected_agents:
        logger.warning(f"No agent connected for streamer {streamer_id}")
        return False

    try:
        ws = connected_agents[streamer_id]
        await ws.send_json({"cmd": "clip"})
        logger.info(f"Sent clip command to streamer {streamer_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send clip command to streamer {streamer_id}: {e}")
        # Remove the dead connection
        if streamer_id in connected_agents:
            del connected_agents[streamer_id]
        return False


@router.get("/agent/status/{streamer_id}")
async def get_agent_status(streamer_id: int, current_user = Depends(get_current_user)):
    """Check if agent is online for a streamer."""
    # Verify ownership
    user_streamer_id = get_streamer_id_for_user(current_user)
    if user_streamer_id != streamer_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    is_online = streamer_id in connected_agents
    return {
        "streamer_id": streamer_id,
        "agent_online": is_online,
        "status": "ready" if is_online else "offline"
    }
