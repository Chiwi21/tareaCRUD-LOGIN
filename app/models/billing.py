from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), index=True
    )
    currency_id: Mapped[int | None] = mapped_column(
        ForeignKey("currencies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="ISSUED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    operation: Mapped[Operation] = relationship(back_populates="invoices")
    currency: Mapped[Currency | None] = relationship(back_populates="invoices")
    payments: Mapped[list[Payment]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )

    @property
    def paid_amount(self) -> Decimal:
        return sum((payment.amount for payment in self.payments), Decimal("0"))

    @property
    def balance(self) -> Decimal:
        return (self.total or Decimal("0")) - self.paid_amount

    @property
    def is_overdue(self) -> bool:
        return (
            self.due_date is not None
            and self.due_date < date.today()
            and self.balance > 0
            and self.status not in ("PAID", "CANCELLED")
        )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payment_date: Mapped[date] = mapped_column(Date, default=date.today)
    method: Mapped[str] = mapped_column(String(20), default="TRANSFER")
    reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
