from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CostScenario(Base):
    __tablename__ = "cost_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    operation: Mapped[Operation] = relationship(back_populates="cost_scenarios")
    items: Mapped[list[CostScenarioItem]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="CostScenarioItem.sort_order",
    )

    @property
    def total(self) -> Decimal:
        return sum((item.amount for item in self.items), Decimal("0"))

    @property
    def product_total(self) -> Decimal:
        return sum(
            (item.amount for item in self.items if item.concept and item.concept.category == "PRODUCT"),
            Decimal("0"),
        )

    @property
    def freight_total(self) -> Decimal:
        return sum(
            (item.amount for item in self.items if item.concept and item.concept.category == "FREIGHT"),
            Decimal("0"),
        )

    @property
    def insurance_total(self) -> Decimal:
        return sum(
            (item.amount for item in self.items if item.concept and item.concept.category == "INSURANCE"),
            Decimal("0"),
        )

    @property
    def charges_total(self) -> Decimal:
        return sum(
            (
                item.amount
                for item in self.items
                if item.concept and item.concept.category in ("CHARGES", "OTHER")
            ),
            Decimal("0"),
        )


class CostScenarioItem(Base):
    __tablename__ = "cost_scenario_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("cost_scenarios.id", ondelete="CASCADE"), index=True
    )
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("cost_concepts.id", ondelete="RESTRICT"), index=True
    )
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    calculation_type: Mapped[str] = mapped_column(String(20), default="FIXED")
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    sort_order: Mapped[int] = mapped_column(default=0)

    scenario: Mapped[CostScenario] = relationship(back_populates="items")
    concept: Mapped[CostConcept] = relationship(back_populates="scenario_items")
