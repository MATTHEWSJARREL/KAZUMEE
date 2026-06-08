import os
import sys
from logging.config import fileConfig
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import create_engine

from alembic import context

# --- PATH LOGIC ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

load_dotenv(os.path.join(root_dir, ".env"))

# --- CONFIGURATION ---
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- IMPORT MODELS (THE CRITICAL PART) ---
from backend.database.models.base import Base
from backend.database.models import (
    command,
    command_log,
    command_result,
    community,
    stream_session,
    streamer,
    viewer,
    user,
    user_session,
    platform_connection,
    stream_event
)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = os.getenv('DATABASE_URL') or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    db_url = os.getenv('DATABASE_URL') or config.get_main_option('sqlalchemy.url')
    
    # Fix for SQLAlchemy 1.4+ (postgres:// to postgresql://)
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    connectable = create_engine(db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
