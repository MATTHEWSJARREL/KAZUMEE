"""fix missing columns for streamers/viewers/commands

Revision ID: 7f1c2a3b4d5e
Revises: 6e2a9d4c1f77
Create Date: 2026-02-06
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "7f1c2a3b4d5e"
down_revision = "6e2a9d4c1f77"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS user_id integer")
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS operation_mode varchar(32) DEFAULT 'hybrid'")
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS auto_approve_min_tier varchar(32) DEFAULT 'vip'")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS user_id integer")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS credits integer DEFAULT 100")
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS total_spent integer DEFAULT 0")
    op.execute("ALTER TABLE commands ADD COLUMN IF NOT EXISTS streamer_id integer")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_streamers_user_id') THEN
                ALTER TABLE streamers
                ADD CONSTRAINT fk_streamers_user_id FOREIGN KEY (user_id) REFERENCES users(id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_viewers_user_id') THEN
                ALTER TABLE viewers
                ADD CONSTRAINT fk_viewers_user_id FOREIGN KEY (user_id) REFERENCES users(id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_commands_streamer_id') THEN
                ALTER TABLE commands
                ADD CONSTRAINT fk_commands_streamer_id FOREIGN KEY (streamer_id) REFERENCES streamers(id);
            END IF;
        END $$;
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_commands_streamer_id ON commands (streamer_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_commands_streamer_id")
    op.execute("ALTER TABLE commands DROP COLUMN IF EXISTS streamer_id")
    op.execute("ALTER TABLE viewers DROP COLUMN IF EXISTS total_spent")
    op.execute("ALTER TABLE viewers DROP COLUMN IF EXISTS credits")
    op.execute("ALTER TABLE viewers DROP COLUMN IF EXISTS user_id")
    op.execute("ALTER TABLE streamers DROP COLUMN IF EXISTS auto_approve_min_tier")
    op.execute("ALTER TABLE streamers DROP COLUMN IF EXISTS operation_mode")
    op.execute("ALTER TABLE streamers DROP COLUMN IF EXISTS user_id")
