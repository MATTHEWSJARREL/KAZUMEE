"""add policy json to streamers

Revision ID: 3d7f0b21c9a1
Revises: 8f2c1a6b9d4e
Create Date: 2026-02-04 21:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3d7f0b21c9a1"
down_revision = "8f2c1a6b9d4e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("streamers", sa.Column("policy_json", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("streamers", "policy_json")
