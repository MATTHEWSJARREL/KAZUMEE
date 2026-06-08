"""add streamer_id to commands and clips

Revision ID: 7b3e2d2df3a1
Revises: 4b9a1f7a92e0
Create Date: 2026-02-04 21:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "7b3e2d2df3a1"
down_revision = "4b9a1f7a92e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("commands", sa.Column("streamer_id", sa.Integer(), nullable=True))
    op.create_index("ix_commands_streamer_id", "commands", ["streamer_id"])
    op.create_foreign_key(
        "fk_commands_streamer_id",
        "commands",
        "streamers",
        ["streamer_id"],
        ["id"],
    )

    op.add_column("clips", sa.Column("streamer_id", sa.Integer(), nullable=True))
    op.create_index("ix_clips_streamer_id", "clips", ["streamer_id"])
    op.create_foreign_key(
        "fk_clips_streamer_id",
        "clips",
        "streamers",
        ["streamer_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_clips_streamer_id", "clips", type_="foreignkey")
    op.drop_index("ix_clips_streamer_id", table_name="clips")
    op.drop_column("clips", "streamer_id")

    op.drop_constraint("fk_commands_streamer_id", "commands", type_="foreignkey")
    op.drop_index("ix_commands_streamer_id", table_name="commands")
    op.drop_column("commands", "streamer_id")
