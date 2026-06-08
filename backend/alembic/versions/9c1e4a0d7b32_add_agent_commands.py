"""add agent commands

Revision ID: 9c1e4a0d7b32
Revises: 3d7f0b21c9a1
Create Date: 2026-02-04 21:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "9c1e4a0d7b32"
down_revision = "3d7f0b21c9a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("streamer_id", sa.Integer(), nullable=False),
        sa.Column("command_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_commands_streamer_id", "agent_commands", ["streamer_id"])
    op.create_index("ix_agent_commands_command_id", "agent_commands", ["command_id"])
    op.create_foreign_key(
        "fk_agent_commands_streamer_id",
        "agent_commands",
        "streamers",
        ["streamer_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_agent_commands_command_id",
        "agent_commands",
        "commands",
        ["command_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_agent_commands_command_id", "agent_commands", type_="foreignkey")
    op.drop_constraint("fk_agent_commands_streamer_id", "agent_commands", type_="foreignkey")
    op.drop_index("ix_agent_commands_command_id", table_name="agent_commands")
    op.drop_index("ix_agent_commands_streamer_id", table_name="agent_commands")
    op.drop_table("agent_commands")
