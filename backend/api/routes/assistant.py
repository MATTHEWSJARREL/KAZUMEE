from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import json

from groq import Groq
from backend.core.auth import get_current_user
from backend.commands.schemas import CommandRequest
from backend.database.session import SessionLocal
from backend.database.models.assistant_message import AssistantMessage
from backend.core.auth import resolve_streamer_id
from backend.database.models.streamer import Streamer

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None
    mode: Optional[str] = "ask"


class ExecuteRequest(BaseModel):
    command: str
    mode: Optional[str] = "command"


@router.post("/api/assistant/chat")
async def assistant_chat(request: Request, payload: ChatRequest):
    user = get_current_user(request, required=False)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="GROQ_API_KEY not configured")

    client = Groq(api_key=api_key)

    mode = payload.mode or "ask"
    if mode not in {"ask", "command"}:
        mode = "ask"

    assistant_prompt = ""
    if user:
        db = SessionLocal()
        try:
            streamer_id = resolve_streamer_id(request, user)
            if streamer_id:
                streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
                settings_json = streamer.settings_json if streamer else None
                assistant_prompt = (
                    (settings_json or {})
                    .get("ai", {})
                    .get("assistantPrompt", "")
                )
        finally:
            db.close()

    system_prompt = (
        "You are Kazumi, an elite AI stream assistant. "
        "Answer clearly and concisely. "
        "Return JSON with fields: reply (string), command (string or null). "
        "If mode is 'ask', command must be null. "
        "If mode is 'command' and the user wants an action, propose a command. "
        "Use command text like a normal streamer would say (e.g., 'switch to gameplay', 'start recording'). "
        "If unsure, set command to null. Do not fabricate integrations or statuses."
    )
    if assistant_prompt:
        system_prompt = f"{system_prompt}\n\nStreamer memory:\n{assistant_prompt}"

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    history = payload.history or []
    if not history and user:
        db = SessionLocal()
        try:
            streamer_id = resolve_streamer_id(request, user)
            query = db.query(AssistantMessage).filter(AssistantMessage.user_id == user.id)
            if streamer_id:
                query = query.filter(AssistantMessage.streamer_id == streamer_id)
            query = query.order_by(AssistantMessage.created_at.desc()).limit(12)
            recent = list(reversed(query.all()))
            history = [
                ChatMessage(role=m.role, content=m.content)
                for m in recent
            ]
        finally:
            db.close()

    for msg in history:
        if msg.role in {"user", "assistant"} and msg.content:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": payload.message})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or "{}"
        parsed = json.loads(content)
        reply = parsed.get("reply") or ""
        command = parsed.get("command") if mode == "command" else None

        if user:
            db = SessionLocal()
            try:
                streamer_id = resolve_streamer_id(request, user)
                db.add(AssistantMessage(
                    user_id=user.id,
                    streamer_id=streamer_id,
                    role="user",
                    mode=mode,
                    content=payload.message,
                ))
                db.add(AssistantMessage(
                    user_id=user.id,
                    streamer_id=streamer_id,
                    role="assistant",
                    mode=mode,
                    content=reply or "",
                    command_text=command,
                ))
                db.commit()
            finally:
                db.close()

        return {
            "status": "ok",
            "message": reply,
            "command": command,
            "executed": False,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/assistant/history")
async def assistant_history(request: Request, mode: str = "ask"):
    user = get_current_user(request, required=True)
    if mode not in {"ask", "command"}:
        mode = "ask"
    db = SessionLocal()
    try:
        streamer_id = resolve_streamer_id(request, user)
        query = db.query(AssistantMessage).filter(
            AssistantMessage.user_id == user.id,
            AssistantMessage.mode == mode,
        )
        if streamer_id:
            query = query.filter(AssistantMessage.streamer_id == streamer_id)
        items = query.order_by(AssistantMessage.created_at.asc()).all()
        return {
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.created_at.isoformat() if m.created_at else "",
                    "command": m.command_text,
                }
                for m in items
            ]
        }
    finally:
        db.close()


@router.post("/api/assistant/execute")
async def assistant_execute(request: Request, payload: ExecuteRequest):
    user = get_current_user(request, required=True)
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    service = getattr(request.app.state, "command_service", None)
    if not service:
        raise HTTPException(status_code=500, detail="Command service not ready")
    result = await service.handle(
        CommandRequest(text=payload.command, is_canonical=False, is_brain=False)
    )
    return {"status": result.status, "message": result.message, "data": result.data}
