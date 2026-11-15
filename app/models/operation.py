from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Operation(Base):
    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    operation_date: Mapped[date] = mapped_column(Date, default=date.today)
    origin_port_id: Mapped[int | None] = mapped_column(
        ForeignKey("ports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    destination_port_id: Mapped[int | None] = mapped_column(
        ForeignKey("ports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    currency_id: Mapped[int | None] = mapped_column(
        ForeignKey("currencies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    incoterm_id: Mapped[int | None] = mapped_column(
        ForeignKey("incoterms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    user: Mapped[User | None] = relationship(back_populates="operations")
    company: Mapped[Company | None] = relationship(back_populates="operations")
    origin_port: Mapped[Port | None] = relationship(
        back_populates="operations_origin", foreign_keys=[origin_port_id]
    )
    destination_port: Mapped[Port | None] = relationship(
        back_populates="operations_destination", foreign_keys=[destination_port_id]
    )
    currency: Mapped[Currency | None] = relationship(back_populates="operations")
    incoterm: Mapped[Incoterm | None] = relationship(back_populates="operations")

    items: Mapped[list[OperationItem]] = relationship(
        back_populates="operation", cascade="all, delete-orphan"
    )
    status_history: Mapped[list[OperationStatusHistory]] = relationship(
        back_populates="operation",
        cascade="all, delete-orphan",
        order_by="OperationStatusHistory.created_at",
    )
    cost_scenarios: Mapped[list[CostScenario]] = relationship(
        back_populates="operation", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="operation", cascade="all, delete-orphan"
    )
    invoices: Mapped[list[Invoice]] = relationship(
        back_populates="operation", cascade="all, delete-orphan"
    )
    alerts: Mapped[list[Alert]] = relationship(
        back_populates="operation", cascade="all, delete-orphan"
    )
    shipment: Mapped[Shipment | None] = relationship(
        back_populates="operation", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def product_subtotal(self) -> Decimal:
        return sum((item.subtotal for item in self.items), Decimal("0"))

    @property
    def selected_scenario(self) -> CostScenario | None:
        for scenario in self.cost_scenarios:
            if scenario.is_selected:
                return scenario
        return None

    @property
    def total_weight(self) -> Decimal:
        return sum(
            ((item.product.weight_kg or Decimal("0")) * item.quantity for item in self.items),
            Decimal("0"),
        )


class OperationItem(Base):
    __tablename__ = "operation_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    operation: Mapped[Operation] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="operation_items")


class OperationStatusHistory(Base):
    __tablename__ = "operation_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20))
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    operation: Mapped[Operation] = relationship(back_populates="status_history")
    changed_by: Mapped[User | None] = relationship(back_populates="status_changes")
