from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    person_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cedula: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    ruc: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    razon_social: Mapped[str | None] = mapped_column(String(150), nullable=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    email_contact: Mapped["UserEmail | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    company: Mapped[Company | None] = relationship(back_populates="users")
    operations: Mapped[list[Operation]] = relationship(
        back_populates="user",
        passive_deletes="all",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user")
    status_changes: Mapped[list[OperationStatusHistory]] = relationship(
        back_populates="changed_by"
    )
    uploaded_documents: Mapped[list[Document]] = relationship(
        back_populates="uploaded_by"
    )
    resolved_alerts: Mapped[list[Alert]] = relationship(back_populates="resolved_by")
