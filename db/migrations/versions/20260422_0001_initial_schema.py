"""Initial user/thread/message schema.

Revision ID: 20260422_0001
Revises:
Create Date: 2026-04-22 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260422_0001"
down_revision = None
branch_labels = None
depends_on = None

user_role = postgresql.ENUM(
    "admin", "operator", "viewer", name="user_role", create_type=False
)
message_role = postgresql.ENUM(
    "user", "assistant", "system", name="message_role", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    message_role.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="operator"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "threads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="New Thread"),
        sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_threads_owner_id", "threads", ["owner_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("thread_id", sa.String(length=36), sa.ForeignKey("threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_thread_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_threads_owner_id", table_name="threads")
    op.drop_table("threads")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    message_role.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
