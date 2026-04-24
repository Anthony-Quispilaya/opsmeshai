from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    record_type: Mapped[str] = mapped_column(String(64), nullable=False, server_default="general")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    policy_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
