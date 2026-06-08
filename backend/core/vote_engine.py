from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Dict, Tuple
import os


class VoteWindow:
    def __init__(self, window_seconds: int, threshold: int):
        self.window_seconds = window_seconds
        self.threshold = threshold
        self._votes: Deque[Tuple[datetime, str]] = deque()

    def _trim(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.window_seconds)
        while self._votes and self._votes[0][0] < cutoff:
            self._votes.popleft()

    def record_vote(self, scene: str) -> Tuple[Dict[str, int], str | None]:
        now = datetime.utcnow()
        self._votes.append((now, scene))
        self._trim(now)

        counts: Dict[str, int] = {}
        for _, s in self._votes:
            counts[s] = counts.get(s, 0) + 1

        winner = None
        for scene_name, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            if count >= self.threshold:
                winner = scene_name
                break

        if winner:
            self._votes.clear()

        return counts, winner


_windows: Dict[int, VoteWindow] = {}


def get_vote_window(streamer_id: int) -> VoteWindow:
    window_seconds = int(os.getenv("VOTE_WINDOW_SEC", "30"))
    threshold = int(os.getenv("VOTE_THRESHOLD", "5"))
    if streamer_id not in _windows:
        _windows[streamer_id] = VoteWindow(window_seconds, threshold)
    return _windows[streamer_id]
