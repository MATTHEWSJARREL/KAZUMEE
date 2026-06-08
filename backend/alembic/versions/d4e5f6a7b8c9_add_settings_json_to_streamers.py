"""add settings_json to streamers

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-09
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE streamers ADD COLUMN IF NOT EXISTS settings_json json")


def downgrade():
    op.execute("ALTER TABLE streamers DROP COLUMN IF EXISTS settings_json")
