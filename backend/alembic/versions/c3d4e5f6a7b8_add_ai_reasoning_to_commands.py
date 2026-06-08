"""add ai_reasoning to commands

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-06
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE commands ADD COLUMN IF NOT EXISTS ai_reasoning varchar")


def downgrade():
    op.execute("ALTER TABLE commands DROP COLUMN IF EXISTS ai_reasoning")
