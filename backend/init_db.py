#!/usr/bin/env python3
"""
Database initialization script for Kazumi.
Creates all necessary tables in the PostgreSQL database.
"""

import os
import sys
from pathlib import Path

# Add the repo root to the Python path
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))

from backend.database.session import SessionLocal, engine, Base
from backend.database.models.clip import Clip
from backend.database.models.streamer import Streamer
from backend.database.models.viewer import Viewer
from backend.database.models.community import Community
from backend.database.models.stream_session import StreamSession
from backend.database.models.command import Command
from backend.database.models.command_result import CommandResult
from backend.database.models.user import User
from backend.database.models.user_session import UserSession
from sqlalchemy import text

def init_database():
    """Initialize the database by creating all tables."""
    try:
        print("🔄 Initializing database...")

        # Create all tables
        Base.metadata.create_all(bind=engine)

        print("✅ Database tables created successfully!")

        # Test the connection
        with SessionLocal() as session:
            result = session.execute(text("SELECT 1"))
            print("✅ Database connection test successful!")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
