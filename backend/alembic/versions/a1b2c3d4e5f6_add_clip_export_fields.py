"""add clip export fields

Revision ID: a1b2c3d4e5f6
Revises: 7f1c2a3b4d5e
Create Date: 2026-02-06 17:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "7f1c2a3b4d5e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("clips") as batch_op:
        batch_op.add_column(sa.Column("export_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("export_preset", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("export_path", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("export_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("clips") as batch_op:
        batch_op.drop_column("export_updated_at")
        batch_op.drop_column("export_path")
        batch_op.drop_column("export_preset")
        batch_op.drop_column("export_status")
