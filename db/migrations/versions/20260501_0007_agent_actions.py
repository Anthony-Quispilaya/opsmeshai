"""Add agent actions table for approval inbox.

Revision ID: 20260501_0007
Revises: 20260423_0006
Create Date: 2026-05-01 16:10:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260501_0007"
down_revision = "20260423_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.75"),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("payload", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("source", sa.String(32), nullable=False, server_default="agent"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_actions_status", "agent_actions", ["status"])
    op.create_index("ix_agent_actions_domain", "agent_actions", ["domain"])
    op.create_index("ix_agent_actions_entity", "agent_actions", ["entity_type", "entity_id"])
    op.create_index("ix_agent_actions_created_at", "agent_actions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_actions_created_at", table_name="agent_actions")
    op.drop_index("ix_agent_actions_entity", table_name="agent_actions")
    op.drop_index("ix_agent_actions_domain", table_name="agent_actions")
    op.drop_index("ix_agent_actions_status", table_name="agent_actions")
    op.drop_table("agent_actions")
