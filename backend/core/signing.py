import hmac
import hashlib
import json
import os


def sign_payload(payload: dict) -> str:
    key = os.getenv("AGENT_SIGNING_KEY", "")
    if not key:
        return ""
    message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key.encode(), message, hashlib.sha256).hexdigest()


def verify_signature(payload: dict, signature: str) -> bool:
    expected = sign_payload(payload)
    if not expected:
        return False
    return hmac.compare_digest(expected, signature)
