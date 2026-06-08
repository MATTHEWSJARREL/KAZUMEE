"""add taste profile to streamers

Revision ID: 6e2a9d4c1f77
Revises: 9c1e4a0d7b32
Create Date: 2026-02-04 22:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "6e2a9d4c1f77"
down_revision = "9c1e4a0d7b32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("streamers", sa.Column("taste_profile", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("streamers", "taste_profile")
