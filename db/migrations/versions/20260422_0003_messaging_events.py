"""Add messaging_events table for webhook idempotency and delivery tracking.

Revision ID: 20260422_0003
Revises: 20260422_0002
Create Date: 2026-04-22 01:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260422_0003"
down_revision = "20260422_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messaging_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("provider_event_id", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.String(length=36), sa.ForeignKey("threads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="accepted"),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column("recipient", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("channel", "provider_event_id", name="uq_messaging_events_channel_provider_event"),
        sa.UniqueConstraint("provider_message_id", name="uq_messaging_events_provider_message_id"),
    )
    op.create_index("ix_messaging_events_channel", "messaging_events", ["channel"], unique=False)
    op.create_index("ix_messaging_events_thread_id", "messaging_events", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messaging_events_thread_id", table_name="messaging_events")
    op.drop_index("ix_messaging_events_channel", table_name="messaging_events")
    op.drop_table("messaging_events")
