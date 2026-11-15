from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int | None] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="WARNING")
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    fingerprint: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    operation: Mapped[Operation | None] = relationship(back_populates="alerts")
    resolved_by: Mapped[User | None] = relationship(back_populates="resolved_alerts")
