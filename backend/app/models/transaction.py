from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    merchant: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False, server_default="Unknown")
    category: Mapped[str] = mapped_column(String(64), nullable=False, server_default="retail")
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
