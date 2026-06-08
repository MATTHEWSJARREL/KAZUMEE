"""add preferences_json to viewers

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-02-16
"""

from alembic import op


revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE viewers ADD COLUMN IF NOT EXISTS preferences_json json")


def downgrade():
    op.execute("ALTER TABLE viewers DROP COLUMN IF EXISTS preferences_json")
