"""add streamer subscription fields

Revision ID: cf31b89a4d12
Revises: bb22cc33dd44
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "cf31b89a4d12"
down_revision = "bb22cc33dd44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "streamers",
        sa.Column("subscription_tier", sa.String(), nullable=False, server_default="free"),
    )
    op.add_column(
        "streamers",
        sa.Column("subscription_status", sa.String(), nullable=False, server_default="inactive"),
    )
    op.add_column(
        "streamers",
        sa.Column("subscription_will_cancel", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("streamers", "subscription_will_cancel")
    op.drop_column("streamers", "subscription_status")
    op.drop_column("streamers", "subscription_tier")

