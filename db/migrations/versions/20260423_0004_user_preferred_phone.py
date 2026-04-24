"""add preferred phone number to users

Revision ID: 20260423_0004
Revises: 20260422_0003
Create Date: 2026-04-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260423_0004"
down_revision = "20260422_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("preferred_phone_number", sa.String(length=32), nullable=True))
    op.create_index(
        "ix_users_preferred_phone_number",
        "users",
        ["preferred_phone_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_preferred_phone_number", table_name="users")
    op.drop_column("users", "preferred_phone_number")
