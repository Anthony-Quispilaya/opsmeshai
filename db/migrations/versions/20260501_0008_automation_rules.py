"""Add automation rules table.

Revision ID: 20260501_0008
Revises: 20260501_0007
Create Date: 2026-05-01 17:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260501_0008"
down_revision = "20260501_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("trigger_type", sa.String(64), nullable=False),
        sa.Column("conditions", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("action_payload", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_automation_rules_enabled", "automation_rules", ["enabled"])
    op.create_index("ix_automation_rules_domain", "automation_rules", ["domain"])


def downgrade() -> None:
    op.drop_index("ix_automation_rules_domain", table_name="automation_rules")
    op.drop_index("ix_automation_rules_enabled", table_name="automation_rules")
    op.drop_table("automation_rules")
