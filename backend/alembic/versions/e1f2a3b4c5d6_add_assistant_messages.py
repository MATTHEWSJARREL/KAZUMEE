"""add assistant_messages

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-02-09
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "e1f2a3b4c5d6"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS assistant_messages (
            id serial PRIMARY KEY,
            user_id integer,
            streamer_id integer,
            role varchar(16) NOT NULL,
            mode varchar(16) NOT NULL DEFAULT 'ask',
            content text NOT NULL,
            command_text text,
            created_at timestamptz DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_assistant_messages_user_id ON assistant_messages (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_assistant_messages_streamer_id ON assistant_messages (streamer_id)")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_assistant_messages_user_id') THEN
                ALTER TABLE assistant_messages
                ADD CONSTRAINT fk_assistant_messages_user_id FOREIGN KEY (user_id) REFERENCES users(id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_assistant_messages_streamer_id') THEN
                ALTER TABLE assistant_messages
                ADD CONSTRAINT fk_assistant_messages_streamer_id FOREIGN KEY (streamer_id) REFERENCES streamers(id);
            END IF;
        END $$;
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS assistant_messages")
