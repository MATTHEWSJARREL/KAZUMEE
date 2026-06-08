from __future__ import annotations

import os
from typing import Optional

from backend.database.models.agent_command import AgentCommand


def _export_output_path(clip_id: int, preset: str) -> str:
    return os.path.join("backend", "data", "exports", f"clip_{clip_id}_{preset}.mp4")


def queue_short_form_export(
    db,
    *,
    clip_id: int,
    streamer_id: Optional[int],
    input_path: str,
    preset: str,
    watermark_text: Optional[str] = None,
    subtitles_path: Optional[str] = None,
):
    job = {
        "clip_id": clip_id,
        "preset": preset,
        "input_path": input_path,
        "output_path": _export_output_path(clip_id, preset),
        "aspect_ratio": "9:16",
        "duration_range": "15-45s",
        "status": "queued",
        "watermark_text": watermark_text,
        "subtitles_path": subtitles_path,
    }

    if streamer_id:
        agent_cmd = AgentCommand(
            streamer_id=streamer_id,
            command_id=None,
            action="export_short_form",
            payload=job,
            status="pending",
        )
        db.add(agent_cmd)
        db.commit()
    return job
