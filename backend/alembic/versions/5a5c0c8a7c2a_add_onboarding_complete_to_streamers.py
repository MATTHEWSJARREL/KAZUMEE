"""add onboarding_complete to streamers

Revision ID: 5a5c0c8a7c2a
Revises: cf31b89a4d12
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5a5c0c8a7c2a"
down_revision = "cf31b89a4d12"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "streamers",
        sa.Column("onboarding_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Ensure existing rows are not NULL (server_default should handle this for most DBs).
    # For databases that don't backfill server_default, uncomment:
    # op.execute("UPDATE streamers SET onboarding_complete = false WHERE onboarding_complete IS NULL")


def downgrade():
    op.drop_column("streamers", "onboarding_complete")

