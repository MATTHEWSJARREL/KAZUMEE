from slowapi import Limiter
from slowapi.util import get_remote_address


limiter = Limiter(key_func=get_remote_address)


# Endpoint-specific rate limits
# - Ingest: 120 req/min (chat/events)
# - Auth: 10 req/min (login/register)
# - AI inference: 30 req/min (catch-up, ask, moderation)
# - Default: 60 req/min (catch-all safety)

RATE_LIMITS = {
    "ingest": "120/minute",
    "auth": "10/minute",
    "ai_inference": "30/minute",
    "default": "60/minute",
}


def get_rate_limit_key(endpoint: str) -> str:
    """Return the rate limit string for a given endpoint."""
    ep = (endpoint or "").strip().lower()

    if ep.startswith("/api/events") or ep == "ingest":
        return RATE_LIMITS["ingest"]
    if ep.startswith("/api/auth") or "/login" in ep or "/register" in ep:
        return RATE_LIMITS["auth"]
    if "/ai" in ep or "/catchup" in ep or "/ask" in ep or "/moderation" in ep:
        return RATE_LIMITS["ai_inference"]

    return RATE_LIMITS["default"]

