from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class MessagingEvent(Base):
    __tablename__ = "messaging_events"
    __table_args__ = (
        UniqueConstraint("channel", "provider_event_id", name="uq_messaging_events_channel_provider_event"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("threads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # inbound | outbound
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted")
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    recipient: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
