"""add platform connections and stream events

Revision ID: 1a2b3c4d5e6f
Revises: 0b7f2c2ddf12
Create Date: 2026-02-04 22:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "1a2b3c4d5e6f"
down_revision = "0b7f2c2ddf12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_connections",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("streamer_id", sa.Integer(), sa.ForeignKey("streamers.id"), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("access_token", sa.String(), nullable=True),
        sa.Column("refresh_token", sa.String(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_platform_connections_streamer_id", "platform_connections", ["streamer_id"])

    op.create_table(
        "stream_events",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("streamer_id", sa.Integer(), sa.ForeignKey("streamers.id"), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_stream_events_streamer_id", "stream_events", ["streamer_id"])


def downgrade() -> None:
    op.drop_index("ix_stream_events_streamer_id", table_name="stream_events")
    op.drop_table("stream_events")
    op.drop_index("ix_platform_connections_streamer_id", table_name="platform_connections")
    op.drop_table("platform_connections")
