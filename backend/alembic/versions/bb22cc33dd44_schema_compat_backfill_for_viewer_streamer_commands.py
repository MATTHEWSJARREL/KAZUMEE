"""schema compat backfill for viewer/streamer/commands

Revision ID: bb22cc33dd44
Revises: aa11bb22cc33
Create Date: 2026-02-20
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "bb22cc33dd44"
down_revision = "aa11bb22cc33"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS user_id integer")
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS operation_mode varchar(32) DEFAULT 'hybrid'")
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS auto_approve_min_tier varchar(32) DEFAULT 'vip'")
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS policy_json json")
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS taste_profile json")
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS settings_json json")

    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS user_id integer")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS active_streamer_id integer")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS platform_user_id varchar")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS is_subscriber boolean DEFAULT false")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS tier varchar(32) DEFAULT 'free'")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS credits integer DEFAULT 100")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS total_spent integer DEFAULT 0")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS preferences_json json")

    op.execute("ALTER TABLE commands ADD COLUMN IF NOT EXISTS streamer_id integer")
    op.execute("ALTER TABLE commands ADD COLUMN IF NOT EXISTS ai_reasoning varchar")
    op.execute("ALTER TABLE commands ADD COLUMN IF NOT EXISTS confidence_score double precision DEFAULT 1.0")
    op.execute("ALTER TABLE commands ADD COLUMN IF NOT EXISTS credit_cost integer DEFAULT 0")

    op.execute("ALTER TABLE stream_events ADD COLUMN IF NOT EXISTS event_id varchar")

    op.execute("CREATE INDEX IF NOT EXISTS ix_commands_streamer_id ON commands (streamer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_viewers_user_id ON viewers (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_viewers_active_streamer_id ON viewers (active_streamer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stream_events_event_id ON stream_events (event_id)")


def downgrade():
    # Keep downgrade conservative for compatibility patches.
    op.execute("DROP INDEX IF EXISTS ix_stream_events_event_id")
    op.execute("DROP INDEX IF EXISTS ix_viewers_active_streamer_id")
    op.execute("DROP INDEX IF EXISTS ix_viewers_user_id")
    op.execute("DROP INDEX IF EXISTS ix_commands_streamer_id")
