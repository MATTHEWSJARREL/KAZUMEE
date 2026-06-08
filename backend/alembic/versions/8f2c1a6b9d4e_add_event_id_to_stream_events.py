"""add event_id to stream events

Revision ID: 8f2c1a6b9d4e
Revises: 1a2b3c4d5e6f
Create Date: 2026-02-04 21:15:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8f2c1a6b9d4e"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("stream_events", sa.Column("event_id", sa.String(), nullable=True))
    op.create_index(
        "ix_stream_events_streamer_platform_event_id",
        "stream_events",
        ["streamer_id", "platform", "event_id"],
    )


def downgrade():
    op.drop_index("ix_stream_events_streamer_platform_event_id", table_name="stream_events")
    op.drop_column("stream_events", "event_id")
