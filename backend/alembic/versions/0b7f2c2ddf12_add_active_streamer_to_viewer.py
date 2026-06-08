"""add active_streamer_id to viewers

Revision ID: 0b7f2c2ddf12
Revises: 7b3e2d2df3a1
Create Date: 2026-02-04 22:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0b7f2c2ddf12"
down_revision = "7b3e2d2df3a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("viewers", sa.Column("active_streamer_id", sa.Integer(), nullable=True))
    op.create_index("ix_viewers_active_streamer_id", "viewers", ["active_streamer_id"])
    op.create_foreign_key(
        "fk_viewers_active_streamer_id",
        "viewers",
        "streamers",
        ["active_streamer_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_viewers_active_streamer_id", "viewers", type_="foreignkey")
    op.drop_index("ix_viewers_active_streamer_id", table_name="viewers")
    op.drop_column("viewers", "active_streamer_id")
