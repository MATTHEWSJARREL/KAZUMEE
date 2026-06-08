"""
Scene aliases for fuzzy resolution.
Maps OBS scene names to lists of alias keywords.
All matching is case-insensitive.
"""

SCENE_ALIASES = {
    "Gameplay": ["game", "gaming", "play"],
    "Chat": ["talk", "discussion", "chatroom", "chat"],
    "Intro": ["start", "beginning", "welcome"],
    "Outro": ["end", "finish", "goodbye"],
    "Break": ["pause", "intermission", "rest", "brb"],
    "Credits": ["thanks", "acknowledgments", "closing"],
}
