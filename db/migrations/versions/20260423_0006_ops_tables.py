"""Add ops tables: transactions, support_tickets, compliance_records, audit_logs

Revision ID: 20260423_0006
Revises: 20260423_0005
Create Date: 2026-04-23 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260423_0006"
down_revision = "20260423_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("merchant", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=False, server_default="Unknown"),
        sa.Column("category", sa.String(64), nullable=False, server_default="retail"),
        sa.Column("risk_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("flagged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_transactions_flagged", "transactions", ["flagged"])
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_identifier", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(64), nullable=False, server_default="general"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("source", sa.String(32), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])

    op.create_table(
        "compliance_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("record_type", sa.String(64), nullable=False, server_default="general"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("policy_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("severity", sa.String(16), nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_compliance_records_status", "compliance_records", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("action_taken", sa.Text, nullable=False),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="system"),
        sa.Column("related_entity_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_domain", "audit_logs", ["domain"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_domain", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_compliance_records_status", table_name="compliance_records")
    op.drop_table("compliance_records")

    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_table("support_tickets")

    op.drop_index("ix_transactions_created_at", table_name="transactions")
    op.drop_index("ix_transactions_flagged", table_name="transactions")
    op.drop_table("transactions")
