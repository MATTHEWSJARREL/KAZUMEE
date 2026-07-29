"""
Groq API Proxy - Routes Groq calls through backend to avoid CORS issues
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from groq import AsyncGroq
import os

router = APIRouter(prefix="/api/groq", tags=["groq"])

# Initialize Groq client (optional for V1 MVP)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Cache for available models
_available_models = None

async def get_available_models():
    """Fetch list of available models from Groq"""
    global _available_models

    if _available_models is None:
        try:
            models = await groq_client.models.list()
            _available_models = [m.id for m in models.data]
            print(f"Available Groq models: {_available_models}")
        except Exception as e:
            print(f"Error fetching models: {e}")
            # Fallback models in order of preference
            _available_models = [
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile",
                "llama2-70b-4096",
                "mixtral-8x7b-32768"
            ]

    return _available_models

async def get_best_model():
    """Get the best available model to use"""
    models = await get_available_models()
    if models:
        return models[0]
    raise Exception("No available models found in Groq API")


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class GroqChatRequest(BaseModel):
    messages: list[ChatMessage]
    system_prompt: str = "You are Kazumee, an AI streaming assistant. Help streamers with their questions about gaming, streaming, and content creation. Keep responses concise and helpful."
    temperature: float = 0.7
    max_tokens: int = 500


@router.post("/chat")
async def chat(request: GroqChatRequest):
    """
    Proxy endpoint for Groq chat completions
    Accepts messages and returns AI response
    """
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Groq API key not configured")

    try:
        # Get the best available model
        model = await get_best_model()
        print(f"Using Groq model: {model}")

        # Build messages with system prompt
        messages = [
            {"role": "system", "content": request.system_prompt},
            *[{"role": msg.role, "content": msg.content} for msg in request.messages]
        ]

        # Call Groq API
        response = await groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return {
            "success": True,
            "response": response.choices[0].message.content
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Groq API error: {str(error)}"
        )
