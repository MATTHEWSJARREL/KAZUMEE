"""add confidence_score and credit_cost to commands

Revision ID: aa11bb22cc33
Revises: f2a3b4c5d6e7
Create Date: 2026-02-20
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "aa11bb22cc33"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE commands ADD COLUMN IF NOT EXISTS confidence_score double precision DEFAULT 1.0")
    op.execute("ALTER TABLE commands ADD COLUMN IF NOT EXISTS credit_cost integer DEFAULT 0")


def downgrade():
    op.execute("ALTER TABLE commands DROP COLUMN IF EXISTS credit_cost")
    op.execute("ALTER TABLE commands DROP COLUMN IF EXISTS confidence_score")
