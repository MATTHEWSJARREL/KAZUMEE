import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text

from backend.core.auth import (
    create_user,
    authenticate_user,
    create_session,
    get_current_user,
    get_streamer_id_for_user,
    resolve_streamer_id,
    hash_password,
    create_stream_access_token,
)
from backend.database.session import SessionLocal
from backend.database.models.streamer import Streamer as StreamerModel
from backend.core.taste import apply_preset
from backend.database.models.viewer import Viewer as ViewerModel
from backend.database.models.user import User as UserModel
from backend.core.rate_limiter import limiter

router = APIRouter()
DEBUG_AUTH_TOKENS = os.getenv("DEBUG_AUTH_TOKENS", "false").lower() == "true"
RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_rate_limit(
    *,
    action: str,
    key: str,
    max_hits: int,
    window_seconds: int,
):
    now = time.time()
    bucket_key = f"{action}:{key}"
    bucket = RATE_LIMIT_BUCKETS[bucket_key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= max_hits:
        retry_after = max(1, int(window_seconds - (now - bucket[0])))
        raise HTTPException(
            status_code=429,
            detail=f"Too many {action} attempts. Try again in {retry_after}s.",
        )
    bucket.append(now)


async def _search_twitch_channels(query: str, limit: int) -> list[dict]:
    client_id = (os.getenv("TWITCH_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("TWITCH_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret or not query:
        return []

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            token_res = await client.post(
                "https://id.twitch.tv/oauth2/token",
                params={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
            )
            if token_res.status_code != 200:
                return []
            access_token = (token_res.json() or {}).get("access_token")
            if not access_token:
                return []

            search_res = await client.get(
                "https://api.twitch.tv/helix/search/channels",
                params={"query": query, "first": max(1, min(limit, 20))},
                headers={
                    "Client-Id": client_id,
                    "Authorization": f"Bearer {access_token}",
                },
            )
            if search_res.status_code != 200:
                return []
            payload = search_res.json() or {}
            channels = payload.get("data") or []
            return [
                {
                    "id": f"twitch:{channel.get('id') or channel.get('broadcaster_login')}",
                    "external_id": channel.get("id"),
                    "display_name": channel.get("display_name") or channel.get("broadcaster_login") or "Unknown",
                    "username": channel.get("broadcaster_login") or channel.get("display_name") or "unknown",
                    "platform": "twitch",
                    "source": "external",
                    "live": bool(channel.get("is_live")),
                    "url": (
                        f"https://www.twitch.tv/{channel.get('broadcaster_login')}"
                        if channel.get("broadcaster_login")
                        else None
                    ),
                }
                for channel in channels
                if channel.get("display_name") or channel.get("broadcaster_login")
            ]
    except Exception:
        return []


async def _search_youtube_channels(query: str, limit: int) -> list[dict]:
    api_key = (os.getenv("YOUTUBE_API_KEY") or "").strip()
    if not api_key or not query:
        return []

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "type": "channel",
                    "q": query,
                    "maxResults": max(1, min(limit, 25)),
                    "key": api_key,
                },
            )
            if res.status_code != 200:
                return []
            payload = res.json() or {}
            items = payload.get("items") or []
            channels = []
            for item in items:
                snippet = item.get("snippet") or {}
                channel_id = ((item.get("id") or {}).get("channelId")) or snippet.get("channelId")
                title = snippet.get("channelTitle") or snippet.get("title")
                if not title:
                    continue
                channels.append(
                    {
                        "id": f"youtube:{channel_id or title}",
                        "external_id": channel_id,
                        "display_name": title,
                        "username": title,
                        "platform": "youtube",
                        "source": "external",
                        "live": False,
                        "url": (
                            f"https://www.youtube.com/channel/{channel_id}"
                            if channel_id
                            else None
                        ),
                    }
                )
            return channels
    except Exception:
        return []


def _rank_streamer_candidate(item: dict, query: str) -> int:
    q = (query or "").strip().lower()
    if not q:
        return 0
    display_name = str(item.get("display_name") or "").lower()
    username = str(item.get("username") or "").lower()
    platform = str(item.get("platform") or "").lower()
    source = str(item.get("source") or "local").lower()
    live = bool(item.get("live"))

    score = 0
    if username == q or display_name == q:
        score += 120
    if username.startswith(q) or display_name.startswith(q):
        score += 90
    if q in username or q in display_name:
        score += 55
    if q in platform:
        score += 20
    if live:
        score += 18
    if source == "local":
        score += 12
    return score

class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str = "viewer"


class LoginRequest(BaseModel):
    email: str
    password: str


class RoleUpdateRequest(BaseModel):
    role: str


class ActiveStreamerRequest(BaseModel):
    streamer_id: int


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class VerifyRequest(BaseModel):
    email: str


class VerifyConfirmRequest(BaseModel):
    token: str


def _ensure_auth_tables(db):
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token varchar(128) PRIMARY KEY,
                user_id integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                kind varchar(16) NOT NULL,
                expires_at timestamptz NOT NULL,
                used boolean NOT NULL DEFAULT false,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_auth_tokens_user_kind ON auth_tokens(user_id, kind)"))
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_flags (
                user_id integer PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                email_verified boolean NOT NULL DEFAULT false,
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.commit()


def _upsert_user_flags(db, user_id: int, email_verified: bool = False):
    db.execute(
        text(
            """
            INSERT INTO user_flags (user_id, email_verified, updated_at)
            VALUES (:user_id, :email_verified, :updated_at)
            ON CONFLICT (user_id)
            DO UPDATE SET
                email_verified = EXCLUDED.email_verified,
                updated_at = EXCLUDED.updated_at
            """
        ),
        {"user_id": user_id, "email_verified": email_verified, "updated_at": datetime.now(timezone.utc)},
    )
    db.commit()


def _get_email_verified(db, user_id: int) -> bool:
    row = db.execute(
        text("SELECT email_verified FROM user_flags WHERE user_id = :user_id LIMIT 1"),
        {"user_id": user_id},
    ).mappings().first()
    if not row:
        return False
    return bool(row["email_verified"])


def _create_auth_token(db, user_id: int, kind: str, ttl_minutes: int) -> str:
    token = secrets.token_urlsafe(32)
    db.execute(
        text(
            """
            INSERT INTO auth_tokens (token, user_id, kind, expires_at, used, created_at)
            VALUES (:token, :user_id, :kind, :expires_at, false, :created_at)
            """
        ),
        {
            "token": token,
            "user_id": user_id,
            "kind": kind,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
            "created_at": datetime.now(timezone.utc),
        },
    )
    db.commit()
    return token


def _consume_auth_token(db, token: str, kind: str) -> int | None:
    row = db.execute(
        text(
            """
            SELECT user_id, expires_at, used
            FROM auth_tokens
            WHERE token = :token AND kind = :kind
            LIMIT 1
            """
        ),
        {"token": token, "kind": kind},
    ).mappings().first()
    if not row:
        return None
    if bool(row["used"]):
        return None
    expires_at = row["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    db.execute(
        text("UPDATE auth_tokens SET used = true WHERE token = :token"),
        {"token": token},
    )
    db.commit()
    return int(row["user_id"])


@router.post("/register")
@limiter.limit("10/minute")
async def register(payload: RegisterRequest, request: Request):
    _enforce_rate_limit(
        action="register",
        key=f"{_client_ip(request)}:{payload.email.lower().strip()}",
        max_hits=8,
        window_seconds=600,
    )
    role = payload.role if payload.role in {"viewer", "streamer"} else "viewer"
    user = create_user(payload.email, payload.password, role=role)
    db = SessionLocal()
    try:
        _ensure_auth_tables(db)
        if role == "streamer":
            streamer = StreamerModel(
                user_id=user.id,
                username=user.email,
                display_name=user.email,
                platform="local",
                taste_profile=apply_preset(None, "balanced"),
            )
            db.add(streamer)
        else:
            viewer = ViewerModel(user_id=user.id, username=user.email)
            db.add(viewer)
        db.commit()
        _upsert_user_flags(db, user.id, email_verified=False)
    finally:
        db.close()
    token = create_session(user.id)
    streamer_id = get_streamer_id_for_user(user)
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "role": user.role},
        "streamer_id": streamer_id,
    }


@router.post("/login")
@limiter.limit("10/minute")
async def login(payload: LoginRequest, request: Request):
    _enforce_rate_limit(
        action="login",
        key=f"{_client_ip(request)}:{payload.email.lower().strip()}",
        max_hits=12,
        window_seconds=600,
    )
    user = authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_session(user.id)
    streamer_id = get_streamer_id_for_user(user)
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "role": user.role},
        "streamer_id": streamer_id,
    }


@router.get("/me")
@limiter.limit("300/minute")
async def me(request: Request):
    user = get_current_user(request, required=False)
    if not user:
        return {"user": None}
    streamer_id = get_streamer_id_for_user(user)
    db = SessionLocal()
    try:
        _ensure_auth_tables(db)
        email_verified = _get_email_verified(db, user.id)
    finally:
        db.close()
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "email_verified": email_verified,
        },
        "streamer_id": streamer_id,
    }


@router.post("/role")
@limiter.limit("10/minute")
async def update_role(payload: RoleUpdateRequest, request: Request):
    user = get_current_user(request, required=True)
    if payload.role not in {"viewer", "streamer"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    db = SessionLocal()
    try:
        db_user = db.query(UserModel).filter(UserModel.id == user.id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        db_user.role = payload.role
        if payload.role == "streamer":
            exists = db.query(StreamerModel).filter(StreamerModel.user_id == db_user.id).first()
            if not exists:
                db.add(StreamerModel(user_id=db_user.id, username=db_user.email, display_name=db_user.email, platform="local"))
        else:
            exists = db.query(ViewerModel).filter(ViewerModel.user_id == db_user.id).first()
            if not exists:
                db.add(ViewerModel(user_id=db_user.id, username=db_user.email))
        db.commit()
        streamer_id = get_streamer_id_for_user(db_user)
        return {"status": "success", "role": db_user.role, "streamer_id": streamer_id}
    finally:
        db.close()


@router.get("/streamers")
@limiter.limit("10/minute")
async def list_streamers(
    request: Request,
    q: str | None = Query(default=None),
    include_external: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=50),
):
    _ = request
    db = SessionLocal()
    try:
        query_text = (q or "").strip()
        base_query = db.query(StreamerModel).order_by(StreamerModel.id.asc())
        if query_text:
            token = f"%{query_text}%"
            base_query = base_query.filter(
                (StreamerModel.display_name.ilike(token))
                | (StreamerModel.username.ilike(token))
                | (StreamerModel.platform.ilike(token))
            )
        items = base_query.limit(max(limit, 40)).all()
        streamers = [
            {
                "id": s.id,
                "display_name": s.display_name or s.username,
                "username": s.username,
                "platform": s.platform,
                "source": "local",
                "live": False,
            }
            for s in items
        ]

        diagnostics = {
            "query": query_text,
            "external_requested": bool(include_external and query_text),
            "external_available": False,
            "twitch_enabled": bool((os.getenv("TWITCH_CLIENT_ID") or "").strip() and (os.getenv("TWITCH_CLIENT_SECRET") or "").strip()),
            "youtube_enabled": bool((os.getenv("YOUTUBE_API_KEY") or "").strip()),
            "twitch_results": 0,
            "youtube_results": 0,
            "message": None,
        }

        if include_external and query_text and len(query_text) >= 2:
            ext_limit = max(3, min(limit, 15))
            twitch_results = await _search_twitch_channels(query_text, ext_limit)
            youtube_results = await _search_youtube_channels(query_text, ext_limit)
            diagnostics["twitch_results"] = len(twitch_results)
            diagnostics["youtube_results"] = len(youtube_results)
            diagnostics["external_available"] = bool(twitch_results or youtube_results)
            if not diagnostics["external_available"]:
                if not diagnostics["twitch_enabled"] and not diagnostics["youtube_enabled"]:
                    diagnostics["message"] = "External streamer discovery is disabled: Twitch and YouTube keys are missing."
                elif not diagnostics["twitch_enabled"]:
                    diagnostics["message"] = "No external results. Twitch discovery is disabled because Twitch API keys are missing."
                elif not diagnostics["youtube_enabled"]:
                    diagnostics["message"] = "No external results. YouTube discovery is disabled because YOUTUBE_API_KEY is missing."
                else:
                    diagnostics["message"] = "No external results from Twitch/YouTube for this query right now."
            streamers.extend(twitch_results)
            streamers.extend(youtube_results)
        elif include_external and query_text and len(query_text) < 2:
            diagnostics["message"] = "Type at least 2 characters to run external streamer discovery."

        deduped: list[dict] = []
        seen: dict[tuple[str, str, str], int] = {}
        for item in streamers:
            key = (
                str(item.get("platform") or "").lower(),
                str(item.get("external_id") or item.get("id") or "").lower(),
                str(item.get("username") or "").lower(),
            )
            ranked_item = {**item, "_score": _rank_streamer_candidate(item, query_text)}
            if key in seen:
                existing_index = seen[key]
                if ranked_item["_score"] > deduped[existing_index]["_score"]:
                    deduped[existing_index] = ranked_item
                continue
            seen[key] = len(deduped)
            deduped.append(ranked_item)

        ranked = sorted(
            deduped,
            key=lambda item: (
                int(item.get("_score") or 0),
                1 if item.get("source") == "local" else 0,
                1 if item.get("live") else 0,
                str(item.get("display_name") or "").lower(),
            ),
            reverse=True,
        )[:limit]

        for item in ranked:
            item.pop("_score", None)

        return {"streamers": ranked, "diagnostics": diagnostics}
    finally:
        db.close()


@router.post("/active-streamer")
@limiter.limit("10/minute")
async def set_active_streamer(payload: ActiveStreamerRequest, request: Request):
    user = get_current_user(request, required=True)
    if user.role != "viewer":
        return {"status": "ignored", "message": "Only viewers set active streamer"}
    db = SessionLocal()
    try:
        viewer = db.query(ViewerModel).filter(ViewerModel.user_id == user.id).first()
        if not viewer:
            viewer = ViewerModel(user_id=user.id, username=user.email)
            db.add(viewer)
        viewer.active_streamer_id = payload.streamer_id
        db.commit()
        return {"status": "success", "streamer_id": payload.streamer_id}
    finally:
        db.close()


class StreamTokenRequest(BaseModel):
    streamer_id: int | None = None
    ttl_seconds: int | None = 300


@router.post("/stream-token")
@limiter.limit("10/minute")
async def issue_stream_token(request: Request, payload: StreamTokenRequest | None = None):
    user = get_current_user(request, required=True)
    desired_streamer = payload.streamer_id if payload else None
    resolved_streamer = resolve_streamer_id(request, user)

    if user.role == "viewer":
        # Viewers are scoped to their selected active streamer.
        # If no active streamer is set yet, allow bootstrap from requested streamer_id.
        if desired_streamer and resolved_streamer and desired_streamer != resolved_streamer:
            raise HTTPException(status_code=403, detail="Viewer cannot request token for a different streamer")
        streamer_id = resolved_streamer
        if streamer_id is None and desired_streamer is not None:
            db = SessionLocal()
            try:
                streamer = (
                    db.query(StreamerModel)
                    .filter(StreamerModel.id == int(desired_streamer))
                    .first()
                )
                if not streamer:
                    raise HTTPException(status_code=404, detail="Streamer not found")
                viewer = db.query(ViewerModel).filter(ViewerModel.user_id == user.id).first()
                if not viewer:
                    viewer = ViewerModel(user_id=user.id, username=user.email)
                    db.add(viewer)
                viewer.active_streamer_id = int(desired_streamer)
                db.commit()
                streamer_id = int(desired_streamer)
            finally:
                db.close()
    else:
        # Streamers can only obtain token for their own tenant.
        streamer_id = resolved_streamer

    if not streamer_id:
        raise HTTPException(status_code=400, detail="streamer_id required")

    ttl = max(60, min(int((payload.ttl_seconds if payload else 300) or 300), 900))
    token = create_stream_access_token(user_id=user.id, streamer_id=streamer_id, ttl_seconds=ttl)
    return {"token": token, "expires_in": ttl, "streamer_id": streamer_id}


@router.post("/password-reset/request")
@limiter.limit("10/minute")
async def password_reset_request(payload: PasswordResetRequest, request: Request):
    _enforce_rate_limit(
        action="password_reset",
        key=f"{_client_ip(request)}:{payload.email.lower().strip()}",
        max_hits=5,
        window_seconds=900,
    )
    db = SessionLocal()
    try:
        _ensure_auth_tables(db)
        user = db.query(UserModel).filter(UserModel.email == payload.email.lower().strip()).first()
        token = None
        if user:
            token = _create_auth_token(db, user.id, kind="reset", ttl_minutes=30)
        response = {"status": "ok", "message": "If this email exists, a reset link has been sent."}
        if token and DEBUG_AUTH_TOKENS:
            response["debug_token"] = token
        return response
    finally:
        db.close()


@router.post("/password-reset/confirm")
@limiter.limit("10/minute")
async def password_reset_confirm(payload: PasswordResetConfirm, request: Request):
    _ = request
    db = SessionLocal()
    try:
        _ensure_auth_tables(db)
        user_id = _consume_auth_token(db, payload.token, kind="reset")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.password_hash = hash_password(payload.new_password)
        db.commit()
        return {"status": "ok", "message": "Password updated successfully."}
    finally:
        db.close()


@router.post("/verify/request")
@limiter.limit("10/minute")
async def verify_request(payload: VerifyRequest, request: Request):
    _enforce_rate_limit(
        action="verify_request",
        key=f"{_client_ip(request)}:{payload.email.lower().strip()}",
        max_hits=5,
        window_seconds=900,
    )
    db = SessionLocal()
    try:
        _ensure_auth_tables(db)
        user = db.query(UserModel).filter(UserModel.email == payload.email.lower().strip()).first()
        token = None
        if user:
            _upsert_user_flags(db, user.id, email_verified=_get_email_verified(db, user.id))
            token = _create_auth_token(db, user.id, kind="verify", ttl_minutes=60 * 24)
        response = {"status": "ok", "message": "Verification email queued."}
        if token and DEBUG_AUTH_TOKENS:
            response["debug_token"] = token
        return response
    finally:
        db.close()


@router.post("/verify/confirm")
@limiter.limit("10/minute")
async def verify_confirm(payload: VerifyConfirmRequest, request: Request):
    _ = request
    db = SessionLocal()
    try:
        _ensure_auth_tables(db)
        user_id = _consume_auth_token(db, payload.token, kind="verify")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        _upsert_user_flags(db, user_id, email_verified=True)
        return {"status": "ok", "message": "Email verified."}
    finally:
        db.close()
