from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    thread_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        SqlEnum(MessageRole, name="message_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    thread = relationship("Thread", back_populates="messages")
