from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), index=True
    )
    document_type_id: Mapped[int] = mapped_column(
        ForeignKey("document_types.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    operation: Mapped[Operation] = relationship(back_populates="documents")
    document_type: Mapped[DocumentType] = relationship(back_populates="documents")
    uploaded_by: Mapped[User | None] = relationship(back_populates="uploaded_documents")

    @property
    def is_expired(self) -> bool:
        return self.expiry_date is not None and self.expiry_date < date.today()

    @property
    def days_to_expire(self) -> int | None:
        if self.expiry_date is None:
            return None
        return (self.expiry_date - date.today()).days
