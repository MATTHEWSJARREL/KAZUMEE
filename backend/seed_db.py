#!/usr/bin/env python3
"""
Seed minimal demo data for development.
Creates a demo streamer + viewer if none exist.
"""
import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))

from backend.database.session import SessionLocal
from backend.database.models.user import User
from backend.database.models.streamer import Streamer
from backend.database.models.viewer import Viewer
from backend.core.auth import create_user


def seed():
    db = SessionLocal()
    try:
        demo_specs = [
            ("demo_streamer@kazumi.ai", "KazumiDemo"),
            ("test_streamer@kazumi.ai", "TestStreamer"),
            ("streamer_alpha@kazumi.ai", "StreamerAlpha"),
        ]

        streamer = None
        for email, display_name in demo_specs:
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                streamer_user = existing_user
            else:
                streamer_user = create_user(email, "demo123", role="streamer")
            existing_streamer = db.query(Streamer).filter(Streamer.user_id == streamer_user.id).first()
            if not existing_streamer:
                existing_streamer = Streamer(
                    user_id=streamer_user.id,
                    username=display_name.lower(),
                    display_name=display_name,
                    platform="local",
                )
                db.add(existing_streamer)
                db.commit()
                db.refresh(existing_streamer)
            elif not existing_streamer.display_name or "@" in str(existing_streamer.display_name):
                existing_streamer.display_name = display_name
                db.commit()
            if streamer is None:
                streamer = existing_streamer

        viewer = db.query(Viewer).first()
        if not viewer:
            existing_user = db.query(User).filter(User.email == "demo_viewer@kazumi.ai").first()
            if existing_user:
                viewer_user = existing_user
            else:
                viewer_user = create_user("demo_viewer@kazumi.ai", "demo123", role="viewer")
            viewer = Viewer(
                user_id=viewer_user.id,
                username=viewer_user.email,
                active_streamer_id=streamer.id,
                tier="free",
            )
            db.add(viewer)
            db.commit()
            db.refresh(viewer)

        return True
    finally:
        db.close()


if __name__ == "__main__":
    ok = seed()
    if ok:
        print("Seed complete.")
