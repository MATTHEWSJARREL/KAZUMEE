"""add viewer actions table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-06 18:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "viewer_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("streamer_id", sa.Integer(), sa.ForeignKey("streamers.id"), nullable=False),
        sa.Column("viewer_id", sa.Integer(), sa.ForeignKey("viewers.id"), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("cost", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_viewer_actions_streamer_id", "viewer_actions", ["streamer_id"])
    op.create_index("ix_viewer_actions_viewer_id", "viewer_actions", ["viewer_id"])


def downgrade():
    op.drop_index("ix_viewer_actions_viewer_id", table_name="viewer_actions")
    op.drop_index("ix_viewer_actions_streamer_id", table_name="viewer_actions")
    op.drop_table("viewer_actions")
