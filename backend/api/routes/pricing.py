import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/api/pricing")
async def get_pricing():
    pricing_path = Path("backend/config/pricing.json")
    if not pricing_path.exists():
        raise HTTPException(status_code=500, detail="Pricing configuration missing")
    try:
        with pricing_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load pricing config: {exc}")
    return data
