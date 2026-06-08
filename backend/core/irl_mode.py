"""IRL Safe Mode - danger phrase detection and auto scene switch."""
import re
import logging
from typing import Optional
from backend.database.session import SessionLocal
from backend.database.models.streamer import Streamer

logger = logging.getLogger(__name__)

DEFAULT_DANGER_PHRASES = [
    r"my address is",
    r"I live in",
    r"my phone number",
    r"don't show this",
    r"wait don't",
    r"actually stop",
    r"my full name",
    r"I live at",
    r"my zip code",
    r"passport|driver's license",
]

class IRLModeMonitor:
    def __init__(self, streamer_id: int):
        self.streamer_id = streamer_id
        self.is_active = False
        self.safe_scene: Optional[str] = None
        self._phrases: list[re.Pattern] = []
        self._custom_phrases: list[str] = []

    def activate(self, safe_scene: str) -> None:
        self.is_active = True
        self.safe_scene = safe_scene
        self._build_patterns()
        logger.info(f"IRL Mode activated for streamer {self.streamer_id}, safe scene: {safe_scene}")

    def deactivate(self) -> None:
        self.is_active = False
        logger.info(f"IRL Mode deactivated for streamer {self.streamer_id}")

    def add_custom_phrase(self, phrase: str) -> None:
        self._custom_phrases.append(phrase.lower().strip())
        self._build_patterns()

    def _build_patterns(self) -> None:
        all_phrases = DEFAULT_DANGER_PHRASES + self._custom_phrases
        self._phrases = [re.compile(p, re.IGNORECASE) for p in all_phrases]

    def check_text(self, text: str) -> bool:
        """Check text for danger phrases. Returns True if match found."""
        if not self.is_active:
            return False
        for pattern in self._phrases:
            if pattern.search(text):
                logger.warning(f"Danger phrase detected: {pattern.pattern}")
                return True
        return False

def get_irl_state(streamer_id: int) -> dict:
    """Get IRL Mode state for streamer."""
    from backend.database.models.streamer import Streamer
    db = SessionLocal()
    try:
        streamer = db.query(Streamer).filter(Streamer.id == streamer_id).first()
        if not streamer:
            return {"is_active": False}
        settings = streamer.settings_json or {}
        return {
            "is_active": settings.get("irl_mode_active", False),
            "safe_scene": settings.get("irl_safe_scene", "BRB"),
            "custom_phrases": settings.get("irl_custom_phrases", []),
        }
    finally:
        db.close()
