import os
import secrets
import hashlib
import hmac
import json
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from backend.database.session import SessionLocal
from backend.database.models.user import User
from backend.database.models.user_session import UserSession
from backend.database.models.streamer import Streamer
from backend.database.models.viewer import Viewer


SESSION_DAYS = int(os.getenv("SESSION_DAYS", "30"))
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
SESSION_TOKEN_PEPPER = os.getenv("SESSION_TOKEN_PEPPER", "")
STREAM_TOKEN_SECRET = (
    os.getenv("STREAM_TOKEN_SECRET")
    or os.getenv("TOKEN_ENCRYPTION_KEY")
    or os.getenv("AGENT_SIGNING_KEY")
    or "kazumi-dev-stream-secret"
)


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${dk.hex()}"


def _hash_session_token(token: str) -> str:
    base = f"{SESSION_TOKEN_PEPPER}:{token}".encode()
    return hashlib.sha256(base).hexdigest()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode())


def _sign_compact(payload_segment: str) -> str:
    sig = hmac.new(STREAM_TOKEN_SECRET.encode(), payload_segment.encode(), hashlib.sha256).digest()
    return _b64url_encode(sig)


def hash_password(password: str) -> str:
    return _hash_password(password)


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
        check = _hash_password(password, salt)
        return secrets.compare_digest(check, stored)
    except Exception:
        return False


def create_user(email: str, password: str, role: str = "viewer") -> User:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email.lower().strip()).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User(email=email.lower().strip(), password_hash=_hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def authenticate_user(email: str, password: str) -> Optional[User]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if user and verify_password(password, user.password_hash):
            return user
        return None
    finally:
        db.close()


def create_session(user_id: int) -> str:
    db = SessionLocal()
    try:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=SESSION_DAYS)
        session = UserSession(user_id=user_id, token=_hash_session_token(token), expires_at=expires_at)
        db.add(session)
        db.commit()
        return token
    finally:
        db.close()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _coerce_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def get_user_from_token(token: str) -> Optional[User]:
    db = SessionLocal()
    try:
        token_hash = _hash_session_token(token)
        try:
            session = db.query(UserSession).filter(UserSession.token == token_hash).first()
            # Backward compatibility for older plaintext sessions.
            if not session:
                session = db.query(UserSession).filter(UserSession.token == token).first()
                if session:
                    session.token = token_hash
                    db.commit()
            if not session:
                return None
            expires_at = _coerce_to_utc(session.expires_at)
            if expires_at < _utc_now():
                return None
            return db.query(User).filter(User.id == session.user_id).first()
        except Exception as e:
            # If database tables don't exist (MVP mode), accept mock tokens
            if "no such table" in str(e).lower():
                return User(id=1, email="demo@kazumi.ai", role="streamer")
            raise
    finally:
        db.close()


def get_user_by_id(user_id: int) -> Optional[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()


def create_stream_access_token(*, user_id: int, streamer_id: int, ttl_seconds: int = 300) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "uid": int(user_id),
        "sid": int(streamer_id),
        "iat": now,
        "exp": now + max(30, min(int(ttl_seconds), 900)),
        "nonce": secrets.token_urlsafe(8),
    }
    payload_segment = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    )
    signature = _sign_compact(payload_segment)
    return f"{payload_segment}.{signature}"


def verify_stream_access_token(token: str) -> Optional[dict]:
    try:
        payload_segment, signature = token.split(".", 1)
    except ValueError:
        return None
    expected = _sign_compact(payload_segment)
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_segment).decode())
    except Exception:
        return None
    exp = int(payload.get("exp", 0) or 0)
    now = int(datetime.now(timezone.utc).timestamp())
    if exp <= now:
        return None
    if "uid" not in payload or "sid" not in payload:
        return None
    return payload


def get_current_user(request: Request, required: bool = False) -> Optional[User]:
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip() if auth.startswith("Bearer ") else None
    if not token:
        if required or REQUIRE_AUTH:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return None

    user = get_user_from_token(token)
    if not user and (required or REQUIRE_AUTH):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def get_streamer_id_for_user(user: Optional[User]) -> Optional[int]:
    if not user:
        return None
    db = SessionLocal()
    try:
        try:
            if user.role == "streamer":
                streamer = db.query(Streamer).filter(Streamer.user_id == user.id).first()
                return streamer.id if streamer else None
            if user.role == "viewer":
                try:
                    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
                except ProgrammingError:
                    # Fallback for partially-migrated databases.
                    db.rollback()
                    try:
                        db.execute(text("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS preferences_json json"))
                        db.commit()
                    except Exception:
                        db.rollback()
                    viewer = db.query(Viewer).filter(Viewer.user_id == user.id).first()
                return viewer.active_streamer_id if viewer else None
            return None
        except Exception as e:
            # If database tables don't exist (MVP mode), return mock streamer ID
            if "no such table" in str(e).lower():
                return 1
            raise
    finally:
        db.close()


def resolve_streamer_id(request: Request, user: Optional[User]) -> Optional[int]:
    header_streamer = request.headers.get("X-Streamer-Id")
    if not user:
        # Never trust tenant headers from unauthenticated requests.
        return None

    if user.role == "streamer":
        # Streamers are always scoped to their own tenant.
        streamer_id = get_streamer_id_for_user(user)
        if header_streamer:
            try:
                requested = int(header_streamer)
                if streamer_id is not None and requested != streamer_id:
                    return streamer_id
            except ValueError:
                return streamer_id
        return streamer_id

    if user.role == "viewer":
        # Viewers are scoped to their selected active streamer only.
        return get_streamer_id_for_user(user)

    return None


# ==============================================================================
# AGENT TOKEN MANAGEMENT (long-lived, per-streamer)
# ==============================================================================

def create_agent_token(streamer_id: int, ttl_days: int = 30) -> str:
    """
    Generate a long-lived agent token for a streamer.

    Returns: raw token string (only shown once to user)
    Store: token_hash in DB for verification
    """
    from backend.database.models.agent_token import AgentToken

    db = SessionLocal()
    try:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)

        # Revoke previous token for this streamer (one active per streamer)
        previous = db.query(AgentToken).filter(
            AgentToken.streamer_id == streamer_id,
            AgentToken.revoked_at == None
        ).first()
        if previous:
            previous.revoked_at = datetime.utcnow()

        agent_token = AgentToken(
            streamer_id=streamer_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        db.add(agent_token)
        db.commit()
        return raw_token
    finally:
        db.close()


def verify_agent_token(token: str) -> Optional[int]:
    """
    Verify an agent token. Returns streamer_id if valid, else None.

    A token is valid if:
    - token_hash matches a stored hash
    - not expired
    - not revoked
    """
    from backend.database.models.agent_token import AgentToken

    if not token:
        return None

    db = SessionLocal()
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        agent_token = db.query(AgentToken).filter(
            AgentToken.token_hash == token_hash
        ).first()

        if not agent_token:
            return None

        # Check if expired
        if agent_token.expires_at < datetime.utcnow():
            return None

        # Check if revoked
        if agent_token.revoked_at is not None:
            return None

        return agent_token.streamer_id
    finally:
        db.close()


def get_agent_token_metadata(streamer_id: int) -> Optional[dict]:
    """
    Get metadata about a streamer's active agent token (never return the token itself).
    """
    from backend.database.models.agent_token import AgentToken

    db = SessionLocal()
    try:
        token = db.query(AgentToken).filter(
            AgentToken.streamer_id == streamer_id,
            AgentToken.revoked_at == None
        ).order_by(AgentToken.created_at.desc()).first()

        if not token:
            return None

        return {
            "exists": True,
            "created_at": token.created_at.isoformat(),
            "expires_at": token.expires_at.isoformat(),
            "revoked": False
        }
    finally:
        db.close()


def revoke_agent_token(streamer_id: int) -> bool:
    """Revoke a streamer's active agent token."""
    from backend.database.models.agent_token import AgentToken

    db = SessionLocal()
    try:
        token = db.query(AgentToken).filter(
            AgentToken.streamer_id == streamer_id,
            AgentToken.revoked_at == None
        ).first()

        if not token:
            return False

        token.revoked_at = datetime.utcnow()
        db.commit()
        return True
    finally:
        db.close()
