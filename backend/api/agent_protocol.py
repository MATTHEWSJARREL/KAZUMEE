"""
Kazumee Agent Protocol

Canonical message shapes and endpoints shared between:
- backend (fastapi routes and websocket handlers)
- agent (kazumee-agent.py running on streamer's PC)

This ensures both sides never drift apart on message format.
"""

import os

# ==============================================================================
# PATHS & URLS
# ==============================================================================

# WebSocket endpoint for agent connections
AGENT_WS_PATH = "/ws/agent"
AGENT_WS_URL = os.getenv("AGENT_WS_URL", "wss://kazumee-production.up.railway.app/ws/agent")

# HTTP endpoints for agent
AGENT_TOKEN_ENDPOINT = "/api/agent/token"
AGENT_INGEST_ENDPOINT = "/api/clips/ingest"
AGENT_STATUS_ENDPOINT = "/api/agent/status"

# ==============================================================================
# MESSAGE SHAPES
# ==============================================================================

# Cloud → Agent: Command to capture a clip
CLIP_COMMAND = {
    "cmd": "clip",
    # No additional fields; agent knows to save replay buffer
}

# Agent → Cloud: Heartbeat/registration
AGENT_ONLINE = {
    "type": "agent_online",
    # Sent on connect to signal ready state
}

# Cloud → Agent: Ping (for keepalive)
PING_MESSAGE = {
    "cmd": "ping",
}

# Agent → Cloud: Pong (response to ping)
PONG_MESSAGE = {
    "type": "pong",
}

# Agent → Cloud: Clip upload notification
CLIP_UPLOADED = {
    "type": "clip_uploaded",
    "clip_id": "<uuid>",
}

# ==============================================================================
# INGEST MULTIPART FORM
# ==============================================================================

# POST /api/clips/ingest
# Content-Type: multipart/form-data
# Fields:
#   - clip: <file> (MP4 video from OBS replay buffer)
#   - ts: <float> (Unix timestamp when moment was detected)
#   - source: <string> ("auto" or "manual")
#
# Headers:
#   - Authorization: Bearer <agent_token>
#
# Response:
#   {
#     "id": "<clip_id>",
#     "status": "processing",
#     "file_size": <bytes>
#   }

# ==============================================================================
# WEBSOCKET AUTH
# ==============================================================================

# Connect to /ws/agent with query param: ?token=<agent_token>
# Upgrade headers:
#   - Authorization: Bearer <agent_token>  (optional, token in query is preferred)

# ==============================================================================
# AGENT TOKEN GENERATION
# ==============================================================================

# GET /api/agent/token
# Headers:
#   - Authorization: Bearer <user_session_token>
#
# Response:
#   {
#     "exists": true,
#     "expires_at": "2026-09-05T12:34:56Z",
#     "revoked": false,
#     "created_at": "2026-08-05T12:34:56Z"
#   }

# POST /api/agent/token?action=regenerate
# Headers:
#   - Authorization: Bearer <user_session_token>
#
# Response (ONLY TIME RAW TOKEN IS RETURNED):
#   {
#     "token": "kazumee_agent_xxx...",  # STORE THIS IMMEDIATELY
#     "expires_at": "2026-09-05T12:34:56Z",
#     "message": "Agent token generated. Store it safely—it won't be shown again."
#   }

# ==============================================================================
# AGENT CONFIG (from env)
# ==============================================================================

AGENT_TOKEN_ENV_VAR = "KAZUMEE_AGENT_TOKEN"
AGENT_WS_URL_ENV_VAR = "KAZUMEE_AGENT_WS_URL"
AGENT_INGEST_URL_ENV_VAR = "KAZUMEE_AGENT_INGEST_URL"
