"""Add item name to transactions.

Revision ID: 20260515_0009
Revises: 20260501_0008
Create Date: 2026-05-15 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260515_0009"
down_revision = "20260501_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("item_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "item_name")
