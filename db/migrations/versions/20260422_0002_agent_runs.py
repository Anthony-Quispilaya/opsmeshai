"""Add agent_runs table for Sprint 3 traces.

Revision ID: 20260422_0002
Revises: 20260422_0001
Create Date: 2026-04-22 00:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260422_0002"
down_revision = "20260422_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("thread_id", sa.String(length=36), sa.ForeignKey("threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_message_id", sa.String(length=36), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "assistant_message_id",
            sa.String(length=36),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trace", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_runs_thread_id", "agent_runs", ["thread_id"], unique=False)
    op.create_index("ix_agent_runs_user_message_id", "agent_runs", ["user_message_id"], unique=False)
    op.create_index(
        "ix_agent_runs_assistant_message_id",
        "agent_runs",
        ["assistant_message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_runs_assistant_message_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_user_message_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_thread_id", table_name="agent_runs")
    op.drop_table("agent_runs")
