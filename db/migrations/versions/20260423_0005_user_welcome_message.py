"""add welcome_message_sent_at to users

Revision ID: 20260423_0005
Revises: 20260423_0004
Create Date: 2026-04-23 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_0005"
down_revision = "20260423_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("welcome_message_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "welcome_message_sent_at")
