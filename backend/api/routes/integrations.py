from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import asyncio
import os
import secrets
import json
import time
import base64
import httpx
from datetime import datetime, timedelta
import hmac
import hashlib

from backend.core.auth import get_current_user, resolve_streamer_id, get_user_from_token
from backend.database.session import SessionLocal
from backend.database.models.platform_connection import PlatformConnection
from backend.database.models.stream_event import StreamEvent
from backend.core.event_store import insert_stream_event
from backend.core.crypto import encrypt_token, decrypt_token
from backend.commands.obs_adapter import obs_bridge

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class ConnectRequest(BaseModel):
    platform: str  # twitch | youtube


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


def _oauth_base_url(request: Request) -> str:
    base = os.getenv("PUBLIC_BASE_URL") or str(request.base_url).rstrip("/")
    return base

def _frontend_base_url() -> str:
    return os.getenv("FRONTEND_BASE_URL") or "http://localhost:5173"


def _build_query(params: dict) -> str:
    return str(httpx.QueryParams(params))


def _oauth_state_secret() -> str:
    return (
        os.getenv("OAUTH_STATE_SECRET")
        or os.getenv("TOKEN_ENCRYPTION_KEY")
        or os.getenv("TWITCH_CLIENT_SECRET")
        or "kazumi-dev-oauth-state"
    )


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode())


def _sign_state_payload(payload_segment: str) -> str:
    digest = hmac.new(_oauth_state_secret().encode(), payload_segment.encode(), hashlib.sha256).digest()
    return _b64url_encode(digest)


def _issue_oauth_state(*, platform: str, user_id: int, streamer_id: int, ttl_seconds: int = 600) -> str:
    now = int(time.time())
    payload = {
        "platform": platform,
        "user_id": int(user_id),
        "streamer_id": int(streamer_id),
        "iat": now,
        "exp": now + max(60, min(int(ttl_seconds), 1800)),
        "nonce": secrets.token_urlsafe(8),
    }
    payload_segment = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    )
    signature = _sign_state_payload(payload_segment)
    return f"{payload_segment}.{signature}"


def _verify_oauth_state(
    state: str,
    *,
    platform: str,
) -> dict | None:
    try:
        payload_segment, signature = state.split(".", 1)
    except ValueError:
        return None
    expected = _sign_state_payload(payload_segment)
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_segment).decode())
    except Exception:
        return None
    if payload.get("platform") != platform:
        return None
    exp = int(payload.get("exp", 0) or 0)
    if exp <= int(time.time()):
        return None
    if not payload.get("user_id") or not payload.get("streamer_id"):
        return None
    return payload


def _twitch_config():
    return {
        "client_id": os.getenv("TWITCH_CLIENT_ID"),
        "client_secret": os.getenv("TWITCH_CLIENT_SECRET"),
        "auth_url": "https://id.twitch.tv/oauth2/authorize",
        "token_url": "https://id.twitch.tv/oauth2/token",
        "scopes": [
            "chat:read",
            "chat:edit",
            "moderator:read:followers",
            "moderator:manage:chat_settings",
            "moderator:manage:banned_users",
            "clips:edit",
        ],
        "webhook_secret": os.getenv("TWITCH_WEBHOOK_SECRET"),
    }


def _youtube_config():
    return {
        "client_id": os.getenv("YOUTUBE_CLIENT_ID"),
        "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET"),
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube"],
    }


def _build_twitch_auth_url(request: Request, state: str) -> str:
    cfg = _twitch_config()
    redirect_uri = f"{_oauth_base_url(request)}/integrations/twitch/oauth/callback"
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(cfg["scopes"]),
        "state": state,
    }
    return cfg["auth_url"] + "?" + _build_query(params)


def _build_youtube_auth_url(request: Request, state: str) -> str:
    cfg = _youtube_config()
    redirect_uri = f"{_oauth_base_url(request)}/integrations/youtube/oauth/callback"
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(cfg["scopes"]),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return cfg["auth_url"] + "?" + _build_query(params)


@router.get("/status")
async def integrations_status(request: Request):
    user = get_current_user(request, required=False)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"connections": []}
    db = SessionLocal()
    try:
        items = db.query(PlatformConnection).filter(PlatformConnection.streamer_id == streamer_id).all()
        return {
            "connections": [
                {"platform": i.platform, "connected": bool(i.access_token)}
                for i in items
            ]
        }
    finally:
        db.close()


@router.post("/connect")
async def connect_platform(request: Request, payload: ConnectRequest):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    platform = (payload.platform or "").strip().lower()
    if platform not in {"twitch", "youtube"}:
        return {"status": "error", "message": "unsupported platform"}

    state = _issue_oauth_state(platform=platform, user_id=user.id, streamer_id=streamer_id)
    if platform == "twitch":
        auth_url = _build_twitch_auth_url(request, state)
    else:
        auth_url = _build_youtube_auth_url(request, state)

    return {
        "status": "ok",
        "platform": platform,
        "auth_url": auth_url,
    }


@router.get("/twitch/oauth/start")
async def twitch_oauth_start(request: Request, state: str | None = None, token: str | None = None):
    oauth_state = state
    if not oauth_state:
        user = get_user_from_token(token) if token else get_current_user(request, required=False)
        streamer_id = resolve_streamer_id(request, user)
        if not user or not streamer_id:
            return {"status": "error", "message": "authenticated session required"}
        oauth_state = _issue_oauth_state(platform="twitch", user_id=user.id, streamer_id=streamer_id)
    return RedirectResponse(_build_twitch_auth_url(request, oauth_state))


@router.get("/youtube/oauth/start")
async def youtube_oauth_start(request: Request, state: str | None = None, token: str | None = None):
    oauth_state = state
    if not oauth_state:
        user = get_user_from_token(token) if token else get_current_user(request, required=False)
        streamer_id = resolve_streamer_id(request, user)
        if not user or not streamer_id:
            return {"status": "error", "message": "authenticated session required"}
        oauth_state = _issue_oauth_state(platform="youtube", user_id=user.id, streamer_id=streamer_id)
    return RedirectResponse(_build_youtube_auth_url(request, oauth_state))


@router.get("/twitch/oauth/callback")
async def twitch_oauth_callback_get(request: Request, code: str, state: str):
    return await _twitch_oauth_callback(request, OAuthCallbackRequest(code=code, state=state))

@router.post("/twitch/oauth/callback")
async def twitch_oauth_callback(request: Request, payload: OAuthCallbackRequest):
    return await _twitch_oauth_callback(request, payload)

async def _twitch_oauth_callback(request: Request, payload: OAuthCallbackRequest):
    state_data = _verify_oauth_state(payload.state, platform="twitch")
    if not state_data:
        return {"status": "error", "message": "invalid or expired oauth state"}
    streamer_id = int(state_data["streamer_id"])

    cfg = _twitch_config()
    redirect_uri = f"{_oauth_base_url(request)}/integrations/twitch/oauth/callback"

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            cfg["token_url"],
            data={
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code": payload.code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )

    if token_res.status_code != 200:
        return {"status": "error", "message": "token exchange failed", "detail": token_res.text}

    token_data = token_res.json()
    _save_connection(streamer_id, "twitch", token_data)
    return RedirectResponse(f"{_frontend_base_url()}/settings?oauth=success&platform=twitch")


@router.get("/youtube/oauth/callback")
async def youtube_oauth_callback_get(request: Request, code: str, state: str):
    return await _youtube_oauth_callback(request, OAuthCallbackRequest(code=code, state=state))

@router.post("/youtube/oauth/callback")
async def youtube_oauth_callback(request: Request, payload: OAuthCallbackRequest):
    return await _youtube_oauth_callback(request, payload)

async def _youtube_oauth_callback(request: Request, payload: OAuthCallbackRequest):
    state_data = _verify_oauth_state(payload.state, platform="youtube")
    if not state_data:
        return {"status": "error", "message": "invalid or expired oauth state"}
    streamer_id = int(state_data["streamer_id"])

    cfg = _youtube_config()
    redirect_uri = f"{_oauth_base_url(request)}/integrations/youtube/oauth/callback"

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            cfg["token_url"],
            data={
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code": payload.code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )

    if token_res.status_code != 200:
        return {"status": "error", "message": "token exchange failed", "detail": token_res.text}

    token_data = token_res.json()
    _save_connection(streamer_id, "youtube", token_data)
    return RedirectResponse(f"{_frontend_base_url()}/settings?oauth=success&platform=youtube")


def _save_connection(streamer_id: int, platform: str, token_data: dict):
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

    db = SessionLocal()
    try:
        conn = (
            db.query(PlatformConnection)
            .filter(
                PlatformConnection.streamer_id == streamer_id,
                PlatformConnection.platform == platform,
            )
            .first()
        )
        enc_access = encrypt_token(access_token)
        enc_refresh = encrypt_token(refresh_token)
        if not conn:
            conn = PlatformConnection(
                streamer_id=streamer_id,
                platform=platform,
                access_token=enc_access,
                refresh_token=enc_refresh,
                token_expires_at=token_expires_at,
                meta={"raw": token_data},
            )
            db.add(conn)
        else:
            conn.access_token = enc_access
            conn.refresh_token = enc_refresh
            conn.token_expires_at = token_expires_at
            conn.meta = {**(conn.meta or {}), "raw": token_data}
        db.commit()
    finally:
        db.close()


@router.post("/refresh")
async def refresh_token(request: Request, payload: dict):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    platform = payload.get("platform")
    db = SessionLocal()
    try:
        conn = (
            db.query(PlatformConnection)
            .filter(
                PlatformConnection.streamer_id == streamer_id,
                PlatformConnection.platform == platform,
            )
            .first()
        )
        if not conn or not conn.refresh_token:
            return {"status": "error", "message": "no refresh token"}

        if platform == "twitch":
            token_data = await _refresh_twitch(decrypt_token(conn.refresh_token))
        elif platform == "youtube":
            token_data = await _refresh_youtube(decrypt_token(conn.refresh_token))
        else:
            return {"status": "error", "message": "unsupported platform"}

        _save_connection(streamer_id, platform, token_data)
        return {"status": "success"}
    finally:
        db.close()


async def _refresh_twitch(refresh_token: str) -> dict:
    cfg = _twitch_config()
    async with httpx.AsyncClient() as client:
        res = await client.post(
            cfg["token_url"],
            data={
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
    if res.status_code != 200:
        raise Exception(res.text)
    return res.json()


async def _refresh_youtube(refresh_token: str) -> dict:
    cfg = _youtube_config()
    async with httpx.AsyncClient() as client:
        res = await client.post(
            cfg["token_url"],
            data={
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
    if res.status_code != 200:
        raise Exception(res.text)
    return res.json()


@router.post("/webhooks/twitch")
async def twitch_eventsub_webhook(request: Request, streamer_id: int | None = None):
    cfg = _twitch_config()
    secret = cfg["webhook_secret"] or ""
    body = await request.body()
    msg_id = request.headers.get("Twitch-Eventsub-Message-Id", "")
    msg_ts = request.headers.get("Twitch-Eventsub-Message-Timestamp", "")
    msg_sig = request.headers.get("Twitch-Eventsub-Message-Signature", "")

    if secret:
        base = msg_id + msg_ts + body.decode()
        computed = "sha256=" + hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, msg_sig):
            return {"status": "error", "message": "invalid signature"}

    data = await request.json()
    if data.get("challenge"):
        return data["challenge"]

    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    event = data.get("event") or {}
    db = SessionLocal()
    try:
        insert_stream_event(
            db,
            streamer_id=streamer_id,
            platform="twitch",
            event_type=data.get("subscription", {}).get("type", "event"),
            event_id=request.headers.get("Twitch-Eventsub-Message-Id"),
            user_id=event.get("chatter_user_id") or event.get("user_id"),
            username=event.get("chatter_user_name") or event.get("user_name"),
            message=(event.get("message") or {}).get("text"),
            payload=data,
        )
        db.commit()
    finally:
        db.close()
    return {"status": "ok"}


@router.post("/twitch/subscribe")
async def twitch_subscribe(request: Request, payload: dict):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    db = SessionLocal()
    try:
        conn = (
            db.query(PlatformConnection)
            .filter(
                PlatformConnection.streamer_id == streamer_id,
                PlatformConnection.platform == "twitch",
            )
            .first()
        )
        if not conn:
            return {"status": "error", "message": "twitch not connected"}

        broadcaster_id = payload.get("broadcaster_id") or (conn.meta or {}).get("broadcaster_id")
        webhook_url = payload.get("webhook_url") or os.getenv("TWITCH_WEBHOOK_URL")
        if not broadcaster_id or not webhook_url:
            return {"status": "error", "message": "broadcaster_id and webhook_url required"}

        cfg = _twitch_config()
        secret = cfg["webhook_secret"] or ""
        headers = {
            "Authorization": f"Bearer {decrypt_token(conn.access_token)}",
            "Client-Id": cfg["client_id"],
            "Content-Type": "application/json",
        }
        body = {
            "type": "channel.chat.message",
            "version": "1",
            "condition": {"broadcaster_user_id": broadcaster_id, "user_id": broadcaster_id},
            "transport": {"method": "webhook", "callback": f"{webhook_url}?streamer_id={streamer_id}", "secret": secret},
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.twitch.tv/helix/eventsub/subscriptions",
                json=body,
                headers=headers,
            )
        if res.status_code >= 300:
            return {"status": "error", "detail": res.text}
        return {"status": "success", "detail": res.json()}
    finally:
        db.close()


@router.post("/youtube/livechat/poll")
async def youtube_livechat_poll(request: Request, payload: dict):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    db = SessionLocal()
    try:
        conn = (
            db.query(PlatformConnection)
            .filter(
                PlatformConnection.streamer_id == streamer_id,
                PlatformConnection.platform == "youtube",
            )
            .first()
        )
        if not conn:
            return {"status": "error", "message": "youtube not connected"}

        live_chat_id = payload.get("live_chat_id") or (conn.meta or {}).get("live_chat_id")
        if not live_chat_id:
            return {"status": "error", "message": "live_chat_id required"}

        headers = {"Authorization": f"Bearer {decrypt_token(conn.access_token)}"}
        params = {"liveChatId": live_chat_id, "part": "snippet,authorDetails"}
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://www.googleapis.com/youtube/v3/liveChat/messages",
                params=params,
                headers=headers,
            )
        if res.status_code >= 300:
            return {"status": "error", "detail": res.text}
        data = res.json()
        items = data.get("items", [])
        for item in items:
            snippet = item.get("snippet", {})
            author = item.get("authorDetails", {})
            insert_stream_event(
                db,
                streamer_id=streamer_id,
                platform="youtube",
                event_type="chat_message",
                event_id=item.get("id"),
                user_id=author.get("channelId"),
                username=author.get("displayName"),
                message=snippet.get("displayMessage"),
                payload=item,
            )
        next_page = data.get("nextPageToken")
        if next_page:
            conn.meta = {**(conn.meta or {}), "next_page_token": next_page}
        db.commit()
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.post("/save-token")
async def save_token(request: Request, payload: dict):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    platform = payload.get("platform")
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    meta = payload.get("meta")

    db = SessionLocal()
    try:
        conn = (
            db.query(PlatformConnection)
            .filter(
                PlatformConnection.streamer_id == streamer_id,
                PlatformConnection.platform == platform,
            )
            .first()
        )
        if not conn:
            conn = PlatformConnection(
                streamer_id=streamer_id,
                platform=platform,
                access_token=encrypt_token(access_token),
                refresh_token=encrypt_token(refresh_token),
                meta=meta,
            )
            db.add(conn)
        else:
            conn.access_token = encrypt_token(access_token)
            conn.refresh_token = encrypt_token(refresh_token)
            conn.meta = meta
        db.commit()
        return {"status": "success"}
    finally:
        db.close()


@router.get("/metadata")
async def get_metadata(request: Request, platform: str | None = None):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    db = SessionLocal()
    try:
        query = db.query(PlatformConnection).filter(PlatformConnection.streamer_id == streamer_id)
        if platform:
            query = query.filter(PlatformConnection.platform == platform)
        items = query.all()
        return {
            "status": "success",
            "connections": [
                {"platform": i.platform, "meta": i.meta or {}}
                for i in items
            ],
        }
    finally:
        db.close()


@router.post("/metadata")
async def update_metadata(request: Request, payload: dict):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    platform = payload.get("platform")
    meta = payload.get("meta") or {}

    db = SessionLocal()
    try:
        conn = (
            db.query(PlatformConnection)
            .filter(
                PlatformConnection.streamer_id == streamer_id,
                PlatformConnection.platform == platform,
            )
            .first()
        )
        if not conn:
            conn = PlatformConnection(streamer_id=streamer_id, platform=platform, meta=meta)
            db.add(conn)
        else:
            merged = {**(conn.meta or {}), **meta}
            conn.meta = merged
        db.commit()
        return {"status": "success"}
    finally:
        db.close()


@router.get("/diagnostics")
async def integrations_diagnostics(request: Request):
    user = get_current_user(request, required=True)
    streamer_id = resolve_streamer_id(request, user)
    if not streamer_id:
        return {"status": "error", "message": "streamer_id required"}

    cfg_twitch = _twitch_config()
    cfg_youtube = _youtube_config()

    db = SessionLocal()
    try:
        items = db.query(PlatformConnection).filter(PlatformConnection.streamer_id == streamer_id).all()
        conn_map = {i.platform: i for i in items}
    finally:
        db.close()

    def _conn_status(platform: str):
        c = conn_map.get(platform)
        meta = c.meta if c else {}
        return {
            "connected": bool(c and c.access_token),
            "token_expires_at": c.token_expires_at.isoformat() if c and c.token_expires_at else None,
            "meta": meta or {},
        }

    async def _validate_twitch_connection() -> dict:
        state = _conn_status("twitch")
        if not state["connected"]:
            return {**state, "token_valid": False, "last_error": "not_connected"}

        conn = conn_map.get("twitch")
        if not conn:
            return {**state, "token_valid": False, "last_error": "missing_connection_record"}

        try:
            token = decrypt_token(conn.access_token)
        except Exception:
            return {**state, "token_valid": False, "last_error": "token_decrypt_failed"}

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(
                    "https://id.twitch.tv/oauth2/validate",
                    headers={"Authorization": f"Bearer {token}"},
                )
            if res.status_code != 200:
                return {
                    **state,
                    "token_valid": False,
                    "last_error": f"validate_http_{res.status_code}",
                }
            payload = res.json() or {}
            return {
                **state,
                "token_valid": True,
                "token_scopes": payload.get("scopes") or [],
                "twitch_user_id": payload.get("user_id"),
                "client_id_matches": bool(cfg_twitch.get("client_id")) and payload.get("client_id") == cfg_twitch.get("client_id"),
                "last_error": None,
            }
        except Exception as exc:
            return {**state, "token_valid": False, "last_error": str(exc)}

    async def _validate_youtube_connection() -> dict:
        state = _conn_status("youtube")
        if not state["connected"]:
            return {**state, "token_valid": False, "last_error": "not_connected"}

        conn = conn_map.get("youtube")
        if not conn:
            return {**state, "token_valid": False, "last_error": "missing_connection_record"}

        try:
            token = decrypt_token(conn.access_token)
        except Exception:
            return {**state, "token_valid": False, "last_error": "token_decrypt_failed"}

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(
                    "https://www.googleapis.com/oauth2/v3/tokeninfo",
                    params={"access_token": token},
                )
            if res.status_code != 200:
                return {
                    **state,
                    "token_valid": False,
                    "last_error": f"tokeninfo_http_{res.status_code}",
                }
            payload = res.json() or {}
            return {
                **state,
                "token_valid": True,
                "token_scopes": (payload.get("scope") or "").split(" ") if payload.get("scope") else [],
                "aud_matches_client": bool(cfg_youtube.get("client_id")) and payload.get("aud") == cfg_youtube.get("client_id"),
                "last_error": None,
            }
        except Exception as exc:
            return {**state, "token_valid": False, "last_error": str(exc)}

    async def _validate_obs_connection() -> dict:
        try:
            status = await obs_bridge.get_status()
            return {
                "connected": bool(status.get("connected", False)),
                "streaming": bool(status.get("streaming", False)),
                "recording": bool(status.get("recording", False)),
                "current_scene": status.get("current_scene"),
                "last_error": None if status.get("connected") else "obs_disconnected",
            }
        except Exception as exc:
            return {
                "connected": False,
                "streaming": False,
                "recording": False,
                "current_scene": None,
                "last_error": str(exc),
            }

    async def _validate_groq_connection() -> dict:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {"api_key_set": False, "reachable": False, "last_error": "missing_api_key"}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            if res.status_code != 200:
                return {
                    "api_key_set": True,
                    "reachable": False,
                    "last_error": f"models_http_{res.status_code}",
                }
            data = res.json() or {}
            models = data.get("data") or []
            return {
                "api_key_set": True,
                "reachable": True,
                "model_count": len(models),
                "last_error": None,
            }
        except Exception as exc:
            return {"api_key_set": True, "reachable": False, "last_error": str(exc)}

    twitch_live, youtube_live, obs_live, groq_live = await asyncio.gather(
        _validate_twitch_connection(),
        _validate_youtube_connection(),
        _validate_obs_connection(),
        _validate_groq_connection(),
    )

    diagnostics = {
        "twitch": {
            "client_id_set": bool(cfg_twitch.get("client_id")),
            "client_secret_set": bool(cfg_twitch.get("client_secret")),
            "webhook_secret_set": bool(cfg_twitch.get("webhook_secret")),
            **twitch_live,
        },
        "youtube": {
            "client_id_set": bool(cfg_youtube.get("client_id")),
            "client_secret_set": bool(cfg_youtube.get("client_secret")),
            **youtube_live,
        },
        "obs": obs_live,
        "groq": groq_live,
        "public_base_url": _oauth_base_url(request),
        "frontend_base_url": _frontend_base_url(),
    }

    return {"status": "ok", "diagnostics": diagnostics}
